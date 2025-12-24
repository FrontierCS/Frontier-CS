import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, RowLens, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Mask for M dimensions
    mask_m = offs_m < M
    
    # Load row lengths for the current block of queries
    # RowLens is shape (M,)
    r_lens = tl.load(RowLens + offs_m, mask=mask_m, other=0).to(tl.int32)
    
    # Determine the maximum length (N dimension) we need to process for this block
    limit = tl.max(r_lens)
    
    # Initialize accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)
    
    # Offsets for D dimension
    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    # Load Q block: (BLOCK_M, BLOCK_DMODEL)
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Loop over K/V blocks
    start_n = 0
    while start_n < limit:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Load K block: (BLOCK_N, BLOCK_DMODEL)
        mask_n = offs_n < N
        k_ptrs = K + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute Attention Scores: QK^T
        # q: (BM, D), k: (BN, D) -> qk: (BM, BN)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Apply Ragged Masking
        # Valid where offs_n < r_lens[i]
        mask_context = offs_n[None, :] < r_lens[:, None]
        qk = tl.where(mask_context, qk, float("-inf"))
        
        # Online Softmax Update
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        row_sum = tl.sum(p, 1)
        l_new = l_i * alpha + row_sum
        
        # Update accumulator with new scaling
        acc = acc * alpha[:, None]
        
        # Load V block: (BLOCK_N, BLOCK_DMODEL)
        v_ptrs = V + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Accumulate weighted values: P @ V
        # p: (BM, BN), v: (BN, D) -> (BM, D)
        acc += tl.dot(p.to(tl.float16), v)
        
        # Update statistics
        m_i = m_new
        l_i = l_new
        
        start_n += BLOCK_N
        
    # Finalize Output
    # Handle division by zero for fully masked rows
    out = acc / l_i[:, None]
    out = tl.where(l_i[:, None] > 0, out, 0.0)
    
    # Store result
    out_ptrs = Out + (offs_m[:, None] * stride_om + offs_d[None, :] * stride_od)
    tl.store(out_ptrs, out.to(Out.dtype.element_ty), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    # Input validation
    M, D = Q.shape
    N, Dv = V.shape
    
    assert K.shape[1] == D
    assert V.shape[0] == N
    assert row_lens.shape[0] == M
    
    # Allocate output
    Out = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    
    # Tuning parameters
    # L4 GPU optimization
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = D
    
    grid = (triton.cdiv(M, BLOCK_M), 1, 1)
    sm_scale = 1.0 / (D ** 0.5)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, Out,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        Out.stride(0), Out.stride(1),
        sm_scale,
        M, N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        num_warps=4,
        num_stages=2
    )
    
    return Out
"""
        return {"code": code}
