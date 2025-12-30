import torch
import triton
import triton.language as tl
import math
import sys
import inspect

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 4}, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 4}, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_warps': 4, 'num_stages': 4}, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'num_warps': 4, 'num_stages': 2}, num_stages=2),
    ],
    key=['N_CTX']
)
@triton.jit
def _gdpa_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    sm_scale,
    Z, H, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    # IDs
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H

    # Pointer offsets
    # Base pointers for the sequence/head
    q_base = Q + off_z * stride_qz + off_h * stride_qh
    gq_base = GQ + off_z * stride_qz + off_h * stride_qh
    k_base = K + off_z * stride_kz + off_h * stride_kh
    gk_base = GK + off_z * stride_kz + off_h * stride_kh
    v_base = V + off_z * stride_vz + off_h * stride_vh
    out_base = Out + off_z * stride_oz + off_h * stride_oh

    # Offsets initialization
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_n = tl.arange(0, BLOCK_N)
    
    # Q Block Pointers
    q_ptrs = q_base + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk)
    gq_ptrs = gq_base + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk)
    
    # Mask for Q bounds (M dimension)
    m_mask = offs_m[:, None] < N_CTX
    
    # Load Q and GQ
    q = tl.load(q_ptrs, mask=m_mask, other=0.0)
    gq = tl.load(gq_ptrs, mask=m_mask, other=0.0)
    
    # Apply Gating to Q
    q_gated = q * tl.sigmoid(gq)
    
    # Fuse scaling into Q
    q_gated = q_gated * sm_scale
    
    # Initialize accumulators for streaming softmax
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    # Inner loop over K/V blocks
    # Note: K, GK, V have shape (Z, H, N, D). N matches M in this problem (self-attn).
    # Iterate through all N blocks.
    
    # Pre-calculate stride offsets for N step
    # k_base + (offs_n + step) * stride_kn
    
    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n_curr = start_n + offs_n
        
        # Mask for K/V bounds
        n_mask = offs_n_curr[None, :] < N_CTX
        
        # Load K, GK
        # Transpose logic: we load K as (BLOCK_N, D) then transpose in dot
        k_ptrs = k_base + (offs_n_curr[:, None] * stride_kn + offs_d[None, :] * stride_kk)
        gk_ptrs = gk_base + (offs_n_curr[:, None] * stride_kn + offs_d[None, :] * stride_kk)
        
        k = tl.load(k_ptrs, mask=offs_n_curr[:, None] < N_CTX, other=0.0)
        gk = tl.load(gk_ptrs, mask=offs_n_curr[:, None] < N_CTX, other=0.0)
        
        # Apply Gating to K
        k_gated = k * tl.sigmoid(gk)
        
        # Compute Attention Scores: Q @ K.T
        # Shape: (BLOCK_M, D) @ (D, BLOCK_N) -> (BLOCK_M, BLOCK_N)
        qk = tl.dot(q_gated, tl.trans(k_gated))
        
        # Mask padded parts of N with -inf
        if start_n + BLOCK_N > N_CTX:
            qk = tl.where(n_mask, qk, float("-inf"))
            
        # --- Online Softmax Update ---
        
        # 1. Update max (m_i)
        m_i_new = tl.max(qk, 1)
        m_next = tl.maximum(m_i, m_i_new)
        
        # 2. Compute scaling factors
        # alpha = exp(m_prev - m_next)
        alpha = tl.exp(m_i - m_next)
        # p = exp(qk - m_next)
        p = tl.exp(qk - m_next[:, None])
        
        # 3. Update sum (l_i)
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # 4. Load V
        v_ptrs = v_base + (offs_n_curr[:, None] * stride_vn + offs_d[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=offs_n_curr[:, None] < N_CTX, other=0.0)
        
        # 5. Update accumulator
        # acc = acc * alpha + p @ V
        acc = acc * alpha[:, None]
        # p is fp32, v is fp16. Convert p to fp16 for speed if needed, but keeping p fp16 and acc fp32 is standard
        acc = tl.dot(p.to(tl.float16), v, acc)
        
        # Update running max
        m_i = m_next

    # Finalize Output
    # out = acc / l_i
    acc = acc / l_i[:, None]
    
    # Store Output
    out_ptrs = out_base + (offs_m[:, None] * stride_om + offs_d[None, :] * stride_on)
    tl.store(out_ptrs, acc.to(tl.float16), mask=m_mask)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    """
    # Dimensions
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    # Scale factor
    sm_scale = 1.0 / (D ** 0.5)
    
    # Output tensor
    Out = torch.empty_like(Q)
    
    # Grid configuration
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    # Launch Kernel
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        sm_scale,
        Z, H, M,
        BLOCK_D=D
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns the source code of the current solution.
        """
        return {"code": inspect.getsource(sys.modules[__name__])}