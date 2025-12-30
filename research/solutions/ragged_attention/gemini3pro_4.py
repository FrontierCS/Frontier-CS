import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, ROW_LENS,
    O,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    M, N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Mask for M dimension
    mask_m = offs_m < M
    
    # Load row lengths: shape (BLOCK_M,)
    rl = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0)
    
    # Early exit condition: Max length in this block of queries
    max_rl = tl.max(rl, axis=0)

    # Load Q: shape (BLOCK_M, BLOCK_D)
    offs_d = tl.arange(0, BLOCK_D)
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)

    # Initialize accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Iterate over Key/Value blocks
    for start_n in range(0, N, BLOCK_N):
        # Optimization: skip block if start_n exceeds all row lengths in this query chunk
        if start_n >= max_rl:
            break
            
        cols = start_n + offs_n
        mask_n = cols < N
        
        # Load K block: (BLOCK_N, BLOCK_D)
        # Note: We load K rows corresponding to cols indices
        k_ptrs = K + (cols[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute QK^T: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Ragged Masking
        # Condition: col_idx < row_lens[query_idx]
        mask_ragged = cols[None, :] < rl[:, None]
        mask_combined = mask_ragged & mask_n[None, :]
        
        # Apply mask
        qk = tl.where(mask_combined, qk, float("-inf"))
        
        # Online Softmax
        m_curr = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_curr)
        
        # Compute correction factor alpha = exp(m_i - m_new)
        # Handle -inf case to avoid NaN
        alpha = tl.where(m_i == float("-inf"), 0.0, tl.exp(m_i - m_new))
        
        # Rescale accumulators
        acc = acc * alpha[:, None]
        l_i = l_i * alpha
        
        # Compute probabilities P = exp(QK - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        # Update sum L
        l_curr = tl.sum(p, axis=1)
        l_i += l_curr
        
        # Load V block: (BLOCK_N, BLOCK_DV)
        v_ptrs = V + (cols[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Accumulate O += P @ V
        acc += tl.dot(p.to(tl.float16), v)
        
        # Update max
        m_i = m_new

    # Finalize O = acc / l_i
    # Avoid division by zero for empty rows
    l_recip = 1.0 / (l_i + 1.0e-10)
    o = acc * l_recip[:, None]
    
    # Store output
    o_ptrs = O + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Validation
    assert D == 64
    assert Dv == 64
    
    O = torch.empty((M, Dv), dtype=torch.float16, device=Q.device)
    
    sm_scale = 1.0 / math.sqrt(D)
    
    # Tuning for L4
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64
    num_warps = 4
    num_stages = 3
    
    grid = (triton.cdiv(M, BLOCK_M), 1, 1)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens,
        O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        M, N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    
    return O
"""
        return {"code": code}