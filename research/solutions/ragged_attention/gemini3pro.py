import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, RowLens, Out,
    stride_qm, stride_qk,
    stride_kn, stride_kk,
    stride_vn, stride_vk,
    stride_om, stride_ov,
    sm_scale,
    M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_Dv: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Grid logic
    off_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = off_m < M
    
    # Load row_lens for this block of queries
    rl = tl.load(RowLens + off_m, mask=mask_m, other=0)
    
    # Optimization: Determine the max row length in this block
    # We only need to iterate up to this length
    max_len = tl.max(rl, 0)
    
    # Load Q block: (BLOCK_M, D)
    off_d = tl.arange(0, BLOCK_D)
    q_ptrs = Q + (off_m[:, None] * stride_qm + off_d[None, :] * stride_qk)
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Initialize Accumulators for Streaming Softmax
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    start_n = 0
    off_n = tl.arange(0, BLOCK_N)
    off_dv = tl.arange(0, BLOCK_Dv)
    
    # Loop over K/V blocks
    while start_n < max_len:
        cols = start_n + off_n
        
        # Memory boundary mask for K/V
        mask_k = cols < N
        
        # Load K block: (BLOCK_N, D)
        k_ptrs = K + (cols[:, None] * stride_kn + off_d[None, :] * stride_kk)
        k = tl.load(k_ptrs, mask=mask_k[:, None], other=0.0)
        
        # Compute QK^T scores
        # q: (BLOCK_M, D), k: (BLOCK_N, D) -> qk: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Ragged masking: valid if col < row_len[row]
        mask_ragged = cols[None, :] < rl[:, None]
        qk = tl.where(mask_ragged, qk, float("-inf"))
        
        # -- Streaming Softmax Update --
        
        # 1. Compute local max for this block
        m_curr = tl.max(qk, 1)
        
        # 2. Update running global max
        m_new = tl.maximum(m_i, m_curr)
        
        # 3. Compute scaling factors
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_curr - m_new)
        
        # 4. Compute probabilities (unnormalized)
        p = tl.exp(qk - m_new[:, None])
        
        # 5. Update running sum (denominator)
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # 6. Load V block: (BLOCK_N, Dv)
        v_ptrs = V + (cols[:, None] * stride_vn + off_dv[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=mask_k[:, None], other=0.0)
        
        # 7. Update accumulator
        # We cast p to float16 for efficient Tensor Core usage
        p_v = tl.dot(p.to(tl.float16), v)
        acc = acc * alpha[:, None] + p_v
        
        # Update running max
        m_i = m_new
        
        start_n += BLOCK_N
        
    # Finalize
    out = acc / l_i[:, None]
    
    # Store Output
    out_ptrs = Out + (off_m[:, None] * stride_om + off_dv[None, :] * stride_ov)
    tl.store(out_ptrs, out.to(tl.float16), mask=mask_m[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Configuration
    # BLOCK_M=32 to improve occupancy on small M=512/1024
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_Dv = 64
    
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    grid = ((M + BLOCK_M - 1) // BLOCK_M, 1, 1)
    sm_scale = 1.0 / (D ** 0.5)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        M, N,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D, BLOCK_Dv=BLOCK_Dv,
        num_warps=4, num_stages=2
    )
    
    return O
"""
        return {"code": code}