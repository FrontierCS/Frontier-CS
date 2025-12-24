import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 32, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64}, num_warps=8, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 64}, num_warps=8, num_stages=1),
    ],
    key=['N', 'Dq', 'Dv', 'IS_CAUSAL'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    IS_CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    if pid_z >= Z or pid_h >= H or pid_m >= M:
        return
    
    offs_d = tl.arange(0, BLOCK_D)
    offs_n = tl.arange(0, BLOCK_N)
    
    q_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + pid_m * stride_qm
    k_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    v_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    out_ptr = Out_ptr + pid_z * stride_oz + pid_h * stride_oh + pid_m * stride_om
    
    acc = tl.zeros([BLOCK_D], dtype=tl.float32)
    m_i = tl.full([1], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)
    
    q = tl.load(q_ptr + offs_d * stride_qd, mask=offs_d < Dq, other=0.0).to(tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq * 1.0)
    
    for n_start in range(0, N, BLOCK_N):
        n_offs = n_start + offs_n
        
        if IS_CAUSAL:
            mask_n = n_offs <= pid_m if BLOCK_M == 1 else n_offs < (pid_m + BLOCK_M)
        else:
            mask_n = n_offs < N
        
        k = tl.load(
            k_ptr + n_offs[:, None] * stride_kn + offs_d[None, :] * stride_kd,
            mask=mask_n[:, None] & (offs_d[None, :] < Dq),
            other=0.0
        ).to(tl.float32)
        
        qk = tl.sum(q[None, :] * k, axis=1)
        qk = qk * scale
        
        if IS_CAUSAL and BLOCK_M > 1:
            causal_mask = n_offs < (pid_m + BLOCK_M)
            qk = tl.where(causal_mask, qk, float('-inf'))
        
        m_ij = tl.maximum(m_i, tl.max(qk, axis=0))
        p = tl.exp(qk - m_ij)
        
        if IS_CAUSAL and BLOCK_M > 1:
            p = tl.where(causal_mask, p, 0.0)
        
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + tl.sum(p, axis=0)
        
        v = tl.load(
            v_ptr + n_offs[:, None] * stride_vn + offs_d[None, :] * stride_vd,
            mask=mask_n[:, None] & (offs_d[None, :] < Dv),
            other=0.0
        ).to(tl.float32)
        
        acc = acc * alpha + tl.sum(p[:, None] * v, axis=0)
        m_i = m_ij
    
    acc = acc / l_i
    tl.store(out_ptr + offs_d * stride_od, acc.to(tl.float16), mask=offs_d < Dv)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    Dv = V.shape[-1]
    
    Out = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)
    
    IS_CAUSAL = False
    
    if M == 1:
        BLOCK_M = 1
    else:
        BLOCK_M = triton.next_power_of_2(M)
    
    grid = (Z, H, M)
    
    _decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        IS_CAUSAL,
        BLOCK_M=BLOCK_M,
        BLOCK_N=triton.next_power_of_2(N) if N <= 1024 else 1024,
        BLOCK_D=64
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": 
"""
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 32, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64}, num_warps=8, num_stages=1),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 64}, num_warps=8, num_stages=1),
    ],
    key=['N', 'Dq', 'Dv', 'IS_CAUSAL'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    IS_CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    if pid_z >= Z or pid_h >= H or pid_m >= M:
        return
    
    offs_d = tl.arange(0, BLOCK_D)
    offs_n = tl.arange(0, BLOCK_N)
    
    q_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + pid_m * stride_qm
    k_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    v_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    out_ptr = Out_ptr + pid_z * stride_oz + pid_h * stride_oh + pid_m * stride_om
    
    acc = tl.zeros([BLOCK_D], dtype=tl.float32)
    m_i = tl.full([1], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)
    
    q = tl.load(q_ptr + offs_d * stride_qd, mask=offs_d < Dq, other=0.0).to(tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq * 1.0)
    
    for n_start in range(0, N, BLOCK_N):
        n_offs = n_start + offs_n
        
        if IS_CAUSAL:
            mask_n = n_offs <= pid_m if BLOCK_M == 1 else n_offs < (pid_m + BLOCK_M)
        else:
            mask_n = n_offs < N
        
        k = tl.load(
            k_ptr + n_offs[:, None] * stride_kn + offs_d[None, :] * stride_kd,
            mask=mask_n[:, None] & (offs_d[None, :] < Dq),
            other=0.0
        ).to(tl.float32)
        
        qk = tl.sum(q[None, :] * k, axis=1)
        qk = qk * scale
        
        if IS_CAUSAL and BLOCK_M > 1:
            causal_mask = n_offs < (pid_m + BLOCK_M)
            qk = tl.where(causal_mask, qk, float('-inf'))
        
        m_ij = tl.maximum(m_i, tl.max(qk, axis=0))
        p = tl.exp(qk - m_ij)
        
        if IS_CAUSAL and BLOCK_M > 1:
            p = tl.where(causal_mask, p, 0.0)
        
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + tl.sum(p, axis=0)
        
        v = tl.load(
            v_ptr + n_offs[:, None] * stride_vn + offs_d[None, :] * stride_vd,
            mask=mask_n[:, None] & (offs_d[None, :] < Dv),
            other=0.0
        ).to(tl.float32)
        
        acc = acc * alpha + tl.sum(p[:, None] * v, axis=0)
        m_i = m_ij
    
    acc = acc / l_i
    tl.store(out_ptr + offs_d * stride_od, acc.to(tl.float16), mask=offs_d < Dv)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    Dv = V.shape[-1]
    
    Out = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)
    
    IS_CAUSAL = False
    
    if M == 1:
        BLOCK_M = 1
    else:
        BLOCK_M = triton.next_power_of_2(M)
    
    grid = (Z, H, M)
    
    _decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        IS_CAUSAL,
        BLOCK_M=BLOCK_M,
        BLOCK_N=triton.next_power_of_2(N) if N <= 1024 else 1024,
        BLOCK_D=64
    )
    
    return Out
"""
        }
