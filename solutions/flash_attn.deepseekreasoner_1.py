import torch
import triton
import triton.language as tl
from typing import Optional


@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vv,
    stride_oz, stride_oh, stride_om, stride_ov,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    IS_CAUSAL: tl.constexpr,
    HAS_MASK: tl.constexpr,
    RETURN_LOGSUMEXP: tl.constexpr,
    logsumexp_ptr=None,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
    v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vv
    o_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_ov
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    scale = tl.sqrt(tl.float32(Dq))
    
    for start_n in range(0, N, BLOCK_N):
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        k = tl.load(k_ptrs, mask=start_n + offs_n[:, None] < N, other=0.0)
        v = tl.load(v_ptrs, mask=start_n + offs_n[:, None] < N, other=0.0)
        
        qk = tl.dot(q, k, trans_b=True)
        qk = qk * (1.0 / scale)
        
        if IS_CAUSAL:
            causal_mask = (start_n + offs_n[None, :]) <= offs_m[:, None]
            qk = tl.where(causal_mask, qk, float("-inf"))
        
        m_ij = tl.maximum(m_i, tl.max(qk, 1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij)
        acc = acc * alpha[:, None]
        l_i = l_i * alpha + l_ij
        
        pv = tl.dot(p.to(v.dtype), v)
        acc = acc + pv
        
        m_i = m_ij
        
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn
    
    acc = acc / l_i[:, None]
    tl.store(o_ptrs, acc.to(Out.dtype.element_ty), mask=offs_m[:, None] < M)
    
    if RETURN_LOGSUMEXP:
        logsumexp_ptrs = logsumexp_ptr + pid_z * H * M + pid_h * M + offs_m
        tl.store(logsumexp_ptrs, m_i + tl.log(l_i), mask=offs_m < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = min(64, Dv)
    
    if Dq % 16 != 0 or Dv % 16 != 0:
        BLOCK_M = 32
        BLOCK_N = 32
        BLOCK_D = 32
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        IS_CAUSAL=causal,
        HAS_MASK=False,
        RETURN_LOGSUMEXP=False,
        num_warps=4,
        num_stages=3,
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
from typing import Optional


@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vv,
    stride_oz, stride_oh, stride_om, stride_ov,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    IS_CAUSAL: tl.constexpr,
    HAS_MASK: tl.constexpr,
    RETURN_LOGSUMEXP: tl.constexpr,
    logsumexp_ptr=None,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
    v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vv
    o_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_ov
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    scale = tl.sqrt(tl.float32(Dq))
    
    for start_n in range(0, N, BLOCK_N):
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        k = tl.load(k_ptrs, mask=start_n + offs_n[:, None] < N, other=0.0)
        v = tl.load(v_ptrs, mask=start_n + offs_n[:, None] < N, other=0.0)
        
        qk = tl.dot(q, k, trans_b=True)
        qk = qk * (1.0 / scale)
        
        if IS_CAUSAL:
            causal_mask = (start_n + offs_n[None, :]) <= offs_m[:, None]
            qk = tl.where(causal_mask, qk, float("-inf"))
        
        m_ij = tl.maximum(m_i, tl.max(qk, 1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij)
        acc = acc * alpha[:, None]
        l_i = l_i * alpha + l_ij
        
        pv = tl.dot(p.to(v.dtype), v)
        acc = acc + pv
        
        m_i = m_ij
        
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn
    
    acc = acc / l_i[:, None]
    tl.store(o_ptrs, acc.to(Out.dtype.element_ty), mask=offs_m[:, None] < M)
    
    if RETURN_LOGSUMEXP:
        logsumexp_ptrs = logsumexp_ptr + pid_z * H * M + pid_h * M + offs_m
        tl.store(logsumexp_ptrs, m_i + tl.log(l_i), mask=offs_m < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = min(64, Dv)
    
    if Dq % 16 != 0 or Dv % 16 != 0:
        BLOCK_M = 32
        BLOCK_N = 32
        BLOCK_D = 32
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        IS_CAUSAL=causal,
        HAS_MASK=False,
        RETURN_LOGSUMEXP=False,
        num_warps=4,
        num_stages=3,
    )
    
    return Out
'''
        return {"code": code}
