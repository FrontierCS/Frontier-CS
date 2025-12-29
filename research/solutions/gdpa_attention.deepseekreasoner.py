import torch
import triton
import triton.language as tl
from typing import Optional, Dict, Any
import os

@triton.jit
def _sigmoid(x):
    return 1.0 / (1.0 + tl.exp(-x))

@triton.jit
def _gdpa_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
    USE_CAUSAL: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    mask_m = offs_m < M
    
    Q_block_ptr = tl.make_block_ptr(
        base=Q_ptr + pid_z * stride_qz + pid_h * stride_qh,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    GQ_block_ptr = tl.make_block_ptr(
        base=GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh,
        shape=(M, Dq),
        strides=(stride_gqm, stride_gqd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    Q = tl.load(Q_block_ptr, boundary_check=(0, 1), padding_option="zero")
    GQ = tl.load(GQ_block_ptr, boundary_check=(0, 1), padding_option="zero")
    Qg = Q * _sigmoid(GQ)
    
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    start_n = 0
    for start_n in range(0, N, BLOCK_N):
        offs_n_curr = start_n + offs_n
        mask_n = offs_n_curr < N
        
        K_block_ptr = tl.make_block_ptr(
            base=K_ptr + pid_z * stride_kz + pid_h * stride_kh,
            shape=(N, Dq),
            strides=(stride_kn, stride_kd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        GK_block_ptr = tl.make_block_ptr(
            base=GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh,
            shape=(N, Dq),
            strides=(stride_gkn, stride_gkd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        V_block_ptr = tl.make_block_ptr(
            base=V_ptr + pid_z * stride_vz + pid_h * stride_vh,
            shape=(N, Dv),
            strides=(stride_vn, stride_vd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_DV),
            order=(1, 0)
        )
        
        K = tl.load(K_block_ptr, boundary_check=(0, 1), padding_option="zero")
        GK = tl.load(GK_block_ptr, boundary_check=(0, 1), padding_option="zero")
        V = tl.load(V_block_ptr, boundary_check=(0, 1), padding_option="zero")
        Kg = K * _sigmoid(GK)
        
        S = tl.dot(Qg, tl.trans(Kg))
        S = S * scale
        
        if USE_CAUSAL:
            mask_causal = offs_m[:, None] >= offs_n_curr[None, :]
            S = tl.where(mask_causal & mask_m[:, None] & mask_n[None, :], S, float("-inf"))
        
        m_ij = tl.maximum(m_i, tl.max(S, axis=1))
        p = tl.exp(S - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        alpha = tl.exp(m_i - m_ij) / l_ij
        acc = acc * alpha[:, None]
        
        beta = p / l_ij[:, None]
        acc += tl.dot(beta.to(V.dtype), V)
        
        m_i = m_ij
        l_i = l_ij
    
    Out_block_ptr = tl.make_block_ptr(
        base=Out_ptr + pid_z * stride_oz + pid_h * stride_oh,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DV),
        order=(1, 0)
    )
    tl.store(Out_block_ptr, acc.to(Out_ptr.dtype.element_ty), boundary_check=(0, 1))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    out = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    
    BLOCK_M = 64
    BLOCK_N = 64
    if M <= 512:
        BLOCK_M = 64
        BLOCK_N = 64
    else:
        BLOCK_M = 64
        BLOCK_N = 64
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=triton.next_power_of_2(Dq),
        BLOCK_DV=triton.next_power_of_2(Dv),
        USE_CAUSAL=False,
        num_warps=4,
        num_stages=3
    )
    
    return out

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, Any]:
        code = '''import torch
import triton
import triton.language as tl
from typing import Optional, Dict, Any
import os

@triton.jit
def _sigmoid(x):
    return 1.0 / (1.0 + tl.exp(-x))

@triton.jit
def _gdpa_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
    USE_CAUSAL: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    mask_m = offs_m < M
    
    Q_block_ptr = tl.make_block_ptr(
        base=Q_ptr + pid_z * stride_qz + pid_h * stride_qh,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    GQ_block_ptr = tl.make_block_ptr(
        base=GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh,
        shape=(M, Dq),
        strides=(stride_gqm, stride_gqd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    Q = tl.load(Q_block_ptr, boundary_check=(0, 1), padding_option="zero")
    GQ = tl.load(GQ_block_ptr, boundary_check=(0, 1), padding_option="zero")
    Qg = Q * _sigmoid(GQ)
    
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    start_n = 0
    for start_n in range(0, N, BLOCK_N):
        offs_n_curr = start_n + offs_n
        mask_n = offs_n_curr < N
        
        K_block_ptr = tl.make_block_ptr(
            base=K_ptr + pid_z * stride_kz + pid_h * stride_kh,
            shape=(N, Dq),
            strides=(stride_kn, stride_kd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        GK_block_ptr = tl.make_block_ptr(
            base=GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh,
            shape=(N, Dq),
            strides=(stride_gkn, stride_gkd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        V_block_ptr = tl.make_block_ptr(
            base=V_ptr + pid_z * stride_vz + pid_h * stride_vh,
            shape=(N, Dv),
            strides=(stride_vn, stride_vd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_DV),
            order=(1, 0)
        )
        
        K = tl.load(K_block_ptr, boundary_check=(0, 1), padding_option="zero")
        GK = tl.load(GK_block_ptr, boundary_check=(0, 1), padding_option="zero")
        V = tl.load(V_block_ptr, boundary_check=(0, 1), padding_option="zero")
        Kg = K * _sigmoid(GK)
        
        S = tl.dot(Qg, tl.trans(Kg))
        S = S * scale
        
        if USE_CAUSAL:
            mask_causal = offs_m[:, None] >= offs_n_curr[None, :]
            S = tl.where(mask_causal & mask_m[:, None] & mask_n[None, :], S, float("-inf"))
        
        m_ij = tl.maximum(m_i, tl.max(S, axis=1))
        p = tl.exp(S - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        alpha = tl.exp(m_i - m_ij) / l_ij
        acc = acc * alpha[:, None]
        
        beta = p / l_ij[:, None]
        acc += tl.dot(beta.to(V.dtype), V)
        
        m_i = m_ij
        l_i = l_ij
    
    Out_block_ptr = tl.make_block_ptr(
        base=Out_ptr + pid_z * stride_oz + pid_h * stride_oh,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DV),
        order=(1, 0)
    )
    tl.store(Out_block_ptr, acc.to(Out_ptr.dtype.element_ty), boundary_check=(0, 1))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    out = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    
    BLOCK_M = 64
    BLOCK_N = 64
    if M <= 512:
        BLOCK_M = 64
        BLOCK_N = 64
    else:
        BLOCK_M = 64
        BLOCK_N = 64
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=triton.next_power_of_2(Dq),
        BLOCK_DV=triton.next_power_of_2(Dv),
        USE_CAUSAL=False,
        num_warps=4,
        num_stages=3
    )
    
    return out
'''
        return {"code": code}