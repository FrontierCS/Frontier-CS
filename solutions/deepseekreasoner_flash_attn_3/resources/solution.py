import torch
import triton
import triton.language as tl
import json
import os
from typing import Optional, Dict, Any


@triton.jit
def _fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vv,
    stride_oz, stride_oh, stride_om, stride_ov,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    CAUSAL: tl.constexpr,
    USE_INITIAL_M: tl.constexpr,
):
    # Grid indices
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    # Create block pointers
    Q_block_ptr = tl.make_block_ptr(
        base=Q,
        shape=(M, Dq),
        strides=(stride_qm, stride_qk),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    # Load Q block
    q = tl.load(Q_block_ptr, boundary_check=(0, 1))
    q = q.to(tl.float32)
    
    # Initialize accumulator and stats
    o = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], value=-float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Scale factor
    scale = 1.0 / tl.sqrt(Dq * 1.0)
    
    # Loop over K/V blocks
    for block_n in range(0, tl.cdiv(N, BLOCK_N)):
        # Create block pointers for K and V
        K_block_ptr = tl.make_block_ptr(
            base=K,
            shape=(N, Dq),
            strides=(stride_kn, stride_kk),
            offsets=(block_n * BLOCK_N, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        V_block_ptr = tl.make_block_ptr(
            base=V,
            shape=(N, Dv),
            strides=(stride_vn, stride_vv),
            offsets=(block_n * BLOCK_N, 0),
            block_shape=(BLOCK_N, Dv),
            order=(1, 0)
        )
        
        # Load K and V blocks
        k = tl.load(K_block_ptr, boundary_check=(0, 1)).to(tl.float32)
        v = tl.load(V_block_ptr, boundary_check=(0, 1)).to(tl.float32)
        
        # Compute attention scores
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        # Apply causal mask if needed
        if CAUSAL:
            m_idx = tl.arange(0, BLOCK_M) + pid_m * BLOCK_M
            n_idx = tl.arange(0, BLOCK_N) + block_n * BLOCK_N
            mask = m_idx[:, None] >= n_idx[None, :]
            s = tl.where(mask, s, float('-inf'))
        
        # Streaming softmax update
        m_ij = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        p = tl.exp(s - m_ij)
        
        # Update l_i and accumulate output
        alpha = tl.exp(m_i - m_ij)
        l_ij = alpha * l_i + tl.sum(p, axis=1)
        
        # Update output
        o = o * alpha[:, None] + tl.dot(p.to(v.dtype), v)
        
        # Update stats for next iteration
        m_i = m_ij
        l_i = l_ij
    
    # Normalize output
    o = o / l_i[:, None]
    
    # Store output
    Out_block_ptr = tl.make_block_ptr(
        base=Out,
        shape=(M, Dv),
        strides=(stride_om, stride_ov),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, Dv),
        order=(1, 0)
    )
    tl.store(Out_block_ptr, o.to(Out.dtype.element_ty), boundary_check=(0, 1))


@triton.jit
def _fwd_kernel_small(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vv,
    stride_oz, stride_oh, stride_om, stride_ov,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    CAUSAL: tl.constexpr,
):
    # Grid indices
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    # Pointers
    Q_ptr = Q + pid_batch * stride_qz + pid_head * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    K_ptr = K + pid_batch * stride_kz + pid_head * stride_kh + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kk
    V_ptr = V + pid_batch * stride_vz + pid_head * stride_vh + offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :] * stride_vv
    
    # Load Q
    q = tl.load(Q_ptr, mask=offs_m[:, None] < M, other=0.0).to(tl.float32)
    
    # Initialize
    o = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], value=-float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq * 1.0)
    
    # Loop over N blocks
    for block_n in range(0, tl.cdiv(N, BLOCK_N)):
        offs_n_block = block_n * BLOCK_N + offs_n
        
        # Load K and V
        k = tl.load(K_ptr + offs_n_block[None, :] * stride_kn, 
                   mask=(offs_n_block[None, :] < N) & (offs_d[:, None] < Dq), 
                   other=0.0).to(tl.float32)
        v = tl.load(V_ptr + offs_n_block[:, None] * stride_vn,
                   mask=(offs_n_block[:, None] < N) & (tl.arange(0, Dv)[None, :] < Dv),
                   other=0.0).to(tl.float32)
        
        # Compute attention
        s = tl.dot(q, k)
        s = s * scale
        
        # Causal masking
        if CAUSAL:
            m_idx = offs_m[:, None]
            n_idx = offs_n_block[None, :]
            mask = (m_idx >= n_idx) & (m_idx < M) & (n_idx < N)
            s = tl.where(mask, s, float('-inf'))
        else:
            mask = (offs_m[:, None] < M) & (offs_n_block[None, :] < N)
            s = tl.where(mask, s, float('-inf'))
        
        # Streaming softmax
        m_ij = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        p = tl.exp(s - m_ij)
        
        alpha = tl.exp(m_i - m_ij)
        l_ij = alpha * l_i + tl.sum(p, axis=1)
        
        o = o * alpha[:, None] + tl.dot(p.to(v.dtype), v)
        
        m_i = m_ij
        l_i = l_ij
    
    # Normalize and store
    o = o / l_i[:, None]
    Out_ptr = Out + pid_batch * stride_oz + pid_head * stride_oh + offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * stride_ov
    tl.store(Out_ptr, o.to(Out.dtype.element_ty), mask=offs_m[:, None] < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        causal: Whether to apply causal masking (default True)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    assert Q.dtype == torch.float16, "Q must be float16"
    assert K.dtype == torch.float16, "K must be float16"
    assert V.dtype == torch.float16, "V must be float16"
    
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    assert K.shape[2] == N, "K sequence length must match V"
    assert V.shape[2] == N, "V sequence length must match K"
    assert K.shape[3] == Dq, "K feature dim must match Q"
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Choose kernel configuration based on problem size
    if M <= 2048 and N <= 2048:
        # Use optimized kernel for moderate sizes
        BLOCK_M = 128 if M >= 512 else 64
        BLOCK_N = 64
        BLOCK_D = 64 if Dq >= 64 else Dq
        
        # Adjust block sizes to fit
        while BLOCK_M > M:
            BLOCK_M //= 2
        while BLOCK_N > N:
            BLOCK_N //= 2
        while BLOCK_D > Dq:
            BLOCK_D //= 2
        
        grid = (Z, H, triton.cdiv(M, BLOCK_M))
        
        _fwd_kernel[grid](
            Q, K, V, Out,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
            Z, H, M, N, Dq, Dv,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_D=BLOCK_D,
            CAUSAL=causal,
            USE_INITIAL_M=False,
            num_warps=8 if BLOCK_M >= 128 else 4,
            num_stages=3
        )
    else:
        # Use simpler kernel for very large sequences
        BLOCK_M = 64
        BLOCK_N = 32
        BLOCK_D = min(64, Dq)
        
        grid = (Z, H, triton.cdiv(M, BLOCK_M))
        
        _fwd_kernel_small[grid](
            Q, K, V, Out,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
            Z, H, M, N, Dq, Dv,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_D=BLOCK_D,
            CAUSAL=causal,
            num_warps=4,
            num_stages=2
        )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Get current file path
        current_file = os.path.abspath(__file__)
        
        return {"program_path": current_file}
