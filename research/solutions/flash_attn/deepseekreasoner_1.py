import torch
import triton
import triton.language as tl
import os

@triton.jit
def _fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
    IS_CAUSAL: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Create block pointers for Q
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_Dq)
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + (offs_m[:, None] * stride_qm + offs_dq[None, :])
    
    # Initialize O and m_i, l_i
    offs_dv = tl.arange(0, BLOCK_Dv)
    o_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + (offs_m[:, None] * stride_om + offs_dv[None, :])
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    # Load Q block
    mask_q = (offs_m[:, None] < M) & (offs_dq[None, :] < Dq)
    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    
    # Scale Q
    q = q * (Dq ** -0.5)
    
    # Loop over K/V blocks
    for block_n in range(0, tl.cdiv(N, BLOCK_N)):
        offs_n = block_n * BLOCK_N + tl.arange(0, BLOCK_N)
        
        # Create block pointers for K
        k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + (offs_n[:, None] * stride_kn + offs_dq[None, :])
        mask_k = (offs_n[:, None] < N) & (offs_dq[None, :] < Dq)
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        
        # Create block pointers for V
        v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + (offs_n[:, None] * stride_vn + offs_dv[None, :])
        mask_v = (offs_n[:, None] < N) & (offs_dv[None, :] < Dv)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Compute S = Q @ K^T
        s = tl.dot(q, tl.trans(k))
        
        # Causal masking
        if IS_CAUSAL:
            mask_causal = offs_m[:, None] >= offs_n[None, :]
            s = tl.where(mask_causal, s, float('-inf'))
        
        # Update m_i and l_i with block max
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        m_ij = tl.where(m_ij == float('-inf'), 0.0, m_ij)
        
        # Compute P = exp(S - m_ij)
        p = tl.exp(s - m_ij[:, None])
        
        # Update l_i
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        # Update acc
        alpha = tl.exp(m_i - m_ij) / l_ij
        acc = acc * alpha[:, None]
        
        # Add contribution from current block
        p_v = tl.dot(p.to(v.dtype), v)
        beta = 1.0 / l_ij
        acc = acc + beta[:, None] * p_v
        
        # Update m_i, l_i for next iteration
        m_i = m_ij
        l_i = l_ij
    
    # Write output
    mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, acc.to(Out.dtype.element_ty), mask=mask_o)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Choose block sizes based on sequence length
    if M >= 2048:
        BLOCK_M = 128
        BLOCK_N = 64
    elif M >= 1024:
        BLOCK_M = 64
        BLOCK_N = 64
    else:
        BLOCK_M = 32
        BLOCK_N = 32
    
    BLOCK_Dq = min(Dq, 64)
    BLOCK_Dv = min(Dv, 64)
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    _fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, 
        BLOCK_Dq=BLOCK_Dq, BLOCK_Dv=BLOCK_Dv,
        IS_CAUSAL=causal,
        num_warps=8 if BLOCK_M >= 64 else 4,
        num_stages=4,
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def _fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
    IS_CAUSAL: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Create block pointers for Q
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_Dq)
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + (offs_m[:, None] * stride_qm + offs_dq[None, :])
    
    # Initialize O and m_i, l_i
    offs_dv = tl.arange(0, BLOCK_Dv)
    o_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + (offs_m[:, None] * stride_om + offs_dv[None, :])
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    # Load Q block
    mask_q = (offs_m[:, None] < M) & (offs_dq[None, :] < Dq)
    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    
    # Scale Q
    q = q * (Dq ** -0.5)
    
    # Loop over K/V blocks
    for block_n in range(0, tl.cdiv(N, BLOCK_N)):
        offs_n = block_n * BLOCK_N + tl.arange(0, BLOCK_N)
        
        # Create block pointers for K
        k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + (offs_n[:, None] * stride_kn + offs_dq[None, :])
        mask_k = (offs_n[:, None] < N) & (offs_dq[None, :] < Dq)
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        
        # Create block pointers for V
        v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + (offs_n[:, None] * stride_vn + offs_dv[None, :])
        mask_v = (offs_n[:, None] < N) & (offs_dv[None, :] < Dv)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Compute S = Q @ K^T
        s = tl.dot(q, tl.trans(k))
        
        # Causal masking
        if IS_CAUSAL:
            mask_causal = offs_m[:, None] >= offs_n[None, :]
            s = tl.where(mask_causal, s, float('-inf'))
        
        # Update m_i and l_i with block max
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        m_ij = tl.where(m_ij == float('-inf'), 0.0, m_ij)
        
        # Compute P = exp(S - m_ij)
        p = tl.exp(s - m_ij[:, None])
        
        # Update l_i
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        # Update acc
        alpha = tl.exp(m_i - m_ij) / l_ij
        acc = acc * alpha[:, None]
        
        # Add contribution from current block
        p_v = tl.dot(p.to(v.dtype), v)
        beta = 1.0 / l_ij
        acc = acc + beta[:, None] * p_v
        
        # Update m_i, l_i for next iteration
        m_i = m_ij
        l_i = l_ij
    
    # Write output
    mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, acc.to(Out.dtype.element_ty), mask=mask_o)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Choose block sizes based on sequence length
    if M >= 2048:
        BLOCK_M = 128
        BLOCK_N = 64
    elif M >= 1024:
        BLOCK_M = 64
        BLOCK_N = 64
    else:
        BLOCK_M = 32
        BLOCK_N = 32
    
    BLOCK_Dq = min(Dq, 64)
    BLOCK_Dv = min(Dv, 64)
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    _fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, 
        BLOCK_Dq=BLOCK_Dq, BLOCK_Dv=BLOCK_Dv,
        IS_CAUSAL=causal,
        num_warps=8 if BLOCK_M >= 64 else 4,
        num_stages=4,
    )
    
    return Out
'''
        return {"code": code}