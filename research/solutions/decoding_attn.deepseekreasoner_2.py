import torch
import triton
import triton.language as tl
from typing import Optional, Tuple
import math

@triton.jit
def decoding_attn_kernel(
    q_ptr, k_ptr, v_ptr, o_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
    SCALE: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    # Initialize pointers for Q
    q_ptrs = q_ptr + pid_z * stride_qz + pid_h * stride_qh + \
             offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    mask_m = offs_m < M
    
    # Initialize accumulation
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    # Load Q block
    q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_dq[None, :] < Dq), other=0.0)
    
    # Loop over K/V blocks
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        start_n_idx = start_n * BLOCK_N
        k_ptrs = k_ptr + pid_z * stride_kz + pid_h * stride_kh + \
                 (start_n_idx + offs_n[:, None]) * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = v_ptr + pid_z * stride_vz + pid_h * stride_vh + \
                 (start_n_idx + offs_n[:, None]) * stride_vn + offs_dv[None, :] * stride_vd
        
        # Mask for valid K/V positions
        mask_n = (start_n_idx + offs_n) < N
        mask_k = mask_n[:, None] & (offs_dq[None, :] < Dq)
        mask_v = mask_n[:, None] & (offs_dv[None, :] < Dv)
        
        # Load K, V blocks
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Compute attention scores
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        qk = tl.dot(q, tl.trans(k), out=qk)
        qk = qk * SCALE
        
        # Apply causal mask (decoder attention)
        if start_n_idx + BLOCK_N <= M:
            mask_causal = (start_n_idx + offs_n[None, :]) <= offs_m[:, None]
        else:
            # Handle boundary condition
            n_indices = start_n_idx + offs_n
            m_indices = offs_m[:, None]
            mask_causal = n_indices[None, :] <= m_indices
        
        qk = tl.where(mask_causal & mask_n[None, :], qk, float("-inf"))
        
        # Online softmax update
        m_i_new = tl.maximum(m_i, tl.max(qk, 1))
        alpha = tl.exp(m_i - m_i_new)
        l_i_new = alpha * l_i + tl.sum(tl.exp(qk - m_i_new[:, None]), 1)
        
        # Update accumulation
        beta = tl.exp(qk - m_i_new[:, None])
        acc = acc * alpha[:, None] + tl.dot(beta, v, out_dtype=tl.float32)
        
        # Update m_i and l_i
        m_i = m_i_new
        l_i = l_i_new
    
    # Normalize and store output
    acc = acc / l_i[:, None]
    o_ptrs = o_ptr + pid_z * stride_oz + pid_h * stride_oh + \
             offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & (offs_dv[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    
    Z, H, M, Dq = Q.shape
    _, _, N, Dq_k = K.shape
    _, _, _, Dv = V.shape
    assert Dq == Dq_k, f"Q and K must have same Dq, got {Dq} and {Dq_k}"
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Configuration
    BLOCK_M = 64 if M >= 64 else triton.next_power_of_2(M)
    BLOCK_N = 128 if N >= 128 else triton.next_power_of_2(N)
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    # Heuristics for optimal block sizes
    if M <= 16:
        BLOCK_M = 16
    elif M <= 32:
        BLOCK_M = 32
    elif M <= 128:
        BLOCK_M = 64
    else:
        BLOCK_M = 64
    
    if N <= 256:
        BLOCK_N = 64
    elif N <= 512:
        BLOCK_N = 128
    elif N <= 1024:
        BLOCK_N = 128
    else:
        BLOCK_N = 128
    
    SCALE = 1.0 / math.sqrt(Dq)
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv,
        SCALE
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
from typing import Optional, Tuple
import math

@triton.jit
def decoding_attn_kernel(
    q_ptr, k_ptr, v_ptr, o_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
    SCALE: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    # Initialize pointers for Q
    q_ptrs = q_ptr + pid_z * stride_qz + pid_h * stride_qh + \\
             offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    mask_m = offs_m < M
    
    # Initialize accumulation
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    # Load Q block
    q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_dq[None, :] < Dq), other=0.0)
    
    # Loop over K/V blocks
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        start_n_idx = start_n * BLOCK_N
        k_ptrs = k_ptr + pid_z * stride_kz + pid_h * stride_kh + \\
                 (start_n_idx + offs_n[:, None]) * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = v_ptr + pid_z * stride_vz + pid_h * stride_vh + \\
                 (start_n_idx + offs_n[:, None]) * stride_vn + offs_dv[None, :] * stride_vd
        
        # Mask for valid K/V positions
        mask_n = (start_n_idx + offs_n) < N
        mask_k = mask_n[:, None] & (offs_dq[None, :] < Dq)
        mask_v = mask_n[:, None] & (offs_dv[None, :] < Dv)
        
        # Load K, V blocks
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Compute attention scores
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        qk = tl.dot(q, tl.trans(k), out=qk)
        qk = qk * SCALE
        
        # Apply causal mask (decoder attention)
        if start_n_idx + BLOCK_N <= M:
            mask_causal = (start_n_idx + offs_n[None, :]) <= offs_m[:, None]
        else:
            # Handle boundary condition
            n_indices = start_n_idx + offs_n
            m_indices = offs_m[:, None]
            mask_causal = n_indices[None, :] <= m_indices
        
        qk = tl.where(mask_causal & mask_n[None, :], qk, float("-inf"))
        
        # Online softmax update
        m_i_new = tl.maximum(m_i, tl.max(qk, 1))
        alpha = tl.exp(m_i - m_i_new)
        l_i_new = alpha * l_i + tl.sum(tl.exp(qk - m_i_new[:, None]), 1)
        
        # Update accumulation
        beta = tl.exp(qk - m_i_new[:, None])
        acc = acc * alpha[:, None] + tl.dot(beta, v, out_dtype=tl.float32)
        
        # Update m_i and l_i
        m_i = m_i_new
        l_i = l_i_new
    
    # Normalize and store output
    acc = acc / l_i[:, None]
    o_ptrs = o_ptr + pid_z * stride_oz + pid_h * stride_oh + \\
             offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & (offs_dv[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    
    Z, H, M, Dq = Q.shape
    _, _, N, Dq_k = K.shape
    _, _, _, Dv = V.shape
    assert Dq == Dq_k, f"Q and K must have same Dq, got {Dq} and {Dq_k}"
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Configuration
    BLOCK_M = 64 if M >= 64 else triton.next_power_of_2(M)
    BLOCK_N = 128 if N >= 128 else triton.next_power_of_2(N)
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    # Heuristics for optimal block sizes
    if M <= 16:
        BLOCK_M = 16
    elif M <= 32:
        BLOCK_M = 32
    elif M <= 128:
        BLOCK_M = 64
    else:
        BLOCK_M = 64
    
    if N <= 256:
        BLOCK_N = 64
    elif N <= 512:
        BLOCK_N = 128
    elif N <= 1024:
        BLOCK_N = 128
    else:
        BLOCK_N = 128
    
    SCALE = 1.0 / math.sqrt(Dq)
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv,
        SCALE
    )
    
    return O
'''
        return {"code": code}
