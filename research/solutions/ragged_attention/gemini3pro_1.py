import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, RowLens, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Mask valid queries
    mask_m = offs_m < M
    
    # Load row_lens
    r_lens = tl.load(RowLens + offs_m, mask=mask_m, other=0)
    
    # Optimization: determine maximum length in this block
    # We only need to iterate up to the longest row in this block
    max_rc = tl.max(r_lens, 0)
    
    # Init accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # Offsets for D and Dv
    offs_d = tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    offs_dv = tl.arange(0, BLOCK_DV)
    mask_dv = offs_dv < Dv
    
    # Load Q: [BLOCK_M, BLOCK_D]
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    
    # Iterate over K, V blocks
    start_n = 0
    # Loop condition handles both physical N (implicit via row_lens <= N assumption) 
    # and optimization (skip blocks beyond max_rc)
    while start_n < max_rc:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Physical K/V mask (columns must be < N)
        mask_k_cols = offs_n < N
        
        # Load K: [BLOCK_N, BLOCK_D]
        k_ptrs = K + (offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_k_cols[None, :] & mask_d[:, None], other=0.0)
        
        # Compute QK^T: [BLOCK_M, BLOCK_N]
        qk = tl.dot(q, k)
        qk *= sm_scale
        
        # Masking: Valid if offs_n < row_len AND offs_n < N
        mask_attn = (offs_n[None, :] < r_lens[:, None]) & mask_k_cols[None, :]
        qk = tl.where(mask_attn, qk, float('-inf'))
        
        # Online Softmax Update
        m_curr = tl.max(qk, 1)
        m_next = tl.maximum(m_i, m_curr)
        
        # Safe exponential for alpha
        alpha = tl.exp(m_i - m_next)
        alpha = tl.where(m_next == float('-inf'), 1.0, alpha)
        
        # Safe exponential for p
        p = tl.exp(qk - m_next[:, None])
        p = tl.where(m_next[:, None] == float('-inf'), 0.0, p)
        
        # Update sum exp
        l_curr = tl.sum(p, 1)
        l_i = l_i * alpha + l_curr
        
        # Load V: [BLOCK_N, BLOCK_DV]
        v_ptrs = V + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_k_cols[:, None] & mask_dv[None, :], other=0.0)
        
        # Accumulate output
        acc = acc * alpha[:, None]
        acc += tl.dot(p.to(tl.float16), v)
        
        m_i = m_next
        start_n += BLOCK_N

    # Normalize
    inv_l_i = 1.0 / (l_i + 1.0e-10)
    o = acc * inv_l_i[:, None]
    
    # Store Output: [BLOCK_M, BLOCK_DV]
    o_ptrs = Out + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]
    
    O = torch.empty((M, Dv), dtype=torch.float16, device=Q.device)
    
    # Configuration
    BLOCK_M = 32
    BLOCK_N = 64
    
    # Handle arbitrary D/Dv by finding next power of 2
    def next_pow2(n):
        k = 1
        while k < n: k *= 2
        return k

    BLOCK_D = max(16, next_pow2(D))
    BLOCK_DV = max(16, next_pow2(Dv))
    
    sm_scale = 1.0 / (D ** 0.5)
    
    grid = ( (M + BLOCK_M - 1) // BLOCK_M, )
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        M, N, D, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}