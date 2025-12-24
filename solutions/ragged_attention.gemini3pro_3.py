import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
    ],
    key=['M', 'N'],
)
@triton.jit
def _ragged_attn_kernel(
    Q, K, V, RowLens, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Boundary check for M
    mask_m = offs_m < M
    
    # Load row lengths: shape (M,)
    # These define the valid N count for each query row
    r_lens = tl.load(RowLens + offs_m, mask=mask_m, other=0)
    
    # Initialize pointers for Q, Output
    offs_d = tl.arange(0, BLOCK_D)
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    
    # Accumulators for streaming softmax
    # m_i: max logit
    # l_i: sum of exponentials
    # acc: accumulated attention output
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    # Load Q block
    # Masking required if M is not a multiple of BLOCK_M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Loop over K, V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Load K block: (BLOCK_N, BLOCK_D)
        # Ensure coalesced read: offs_d is inner dimension
        k_ptrs = K + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute scores: Q @ K.T
        # q: (BLOCK_M, D), k: (BLOCK_N, D) -> qk: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Ragged Masking
        # Valid if current column index < row_len for that row
        # offs_n: (BLOCK_N,), r_lens: (BLOCK_M,)
        ragged_mask = offs_n[None, :] < r_lens[:, None]
        
        # Combine with boundary mask_n (needed if N is not multiple of BLOCK_N)
        # and ensure we mask out padding from K loading
        ragged_mask = ragged_mask & mask_n[None, :]
        
        # Apply mask
        qk = tl.where(ragged_mask, qk, float('-inf'))
        
        # Softmax update (streaming)
        m_curr = tl.max(qk, 1) # (BLOCK_M,)
        m_new = tl.maximum(m_i, m_curr)
        
        # Compute exponents
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(qk - m_new[:, None])
        
        # Update denominator
        l_i = l_i * alpha + tl.sum(beta, 1)
        
        # Load V block: (BLOCK_N, BLOCK_D)
        v_ptrs = V + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Update numerator
        # acc = acc * alpha + beta @ V
        acc = acc * alpha[:, None]
        acc += tl.dot(beta.to(tl.float16), v)
        
        # Update max
        m_i = m_new
        
    # Finalize
    # Normalize by sum of weights
    # Add epsilon to avoid division by zero (e.g., if row_len is 0)
    l_recip = 1.0 / (l_i + 1e-6)
    out = acc * l_recip[:, None]
    
    # Store result
    out_ptrs = Out + (offs_m[:, None] * stride_om + offs_d[None, :] * stride_od)
    tl.store(out_ptrs, out.to(tl.float16), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Check constraints
    assert D == 64 and Dv == 64, "Dimension must be 64 for this kernel configuration"
    
    # Allocate output
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    # Launch kernel
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), )
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        M, N,
        BLOCK_D=64
    )
    
    return O
"""
        return {"code": code}
