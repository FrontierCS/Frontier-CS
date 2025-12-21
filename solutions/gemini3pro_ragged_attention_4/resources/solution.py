import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=4, num_stages=3),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_attn_kernel(
    Q_ptr, K_ptr, V_ptr, RowLens_ptr, Out_ptr,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Mask for valid queries
    m_mask = offs_m < M
    
    # Load row_lens
    row_lens = tl.load(RowLens_ptr + offs_m, mask=m_mask, other=0)
    
    # Optimization: compute max row length in this block to skip unnecessary work
    max_len = tl.max(row_lens)

    # Initialize pointers
    offs_d = tl.arange(0, BLOCK_D)
    q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    # Mask Q loading. Note: offs_d < D check handles D < BLOCK_D
    q = tl.load(q_ptrs, mask=m_mask[:, None] & (offs_d[None, :] < D), other=0.0)
    
    # Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # Loop over keys
    for start_n in range(0, N, BLOCK_N):
        # Early exit optimization: if start_n exceeds the max length in this query block, stop
        if start_n >= max_len:
            break
            
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N
        
        # Load K
        k_ptrs = K_ptr + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_d[None, :] < D), other=0.0)
        
        # Compute scores
        # q: (BLOCK_M, D), k: (BLOCK_N, D) -> (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Masking
        # Valid if offs_n < row_lens
        mask = (offs_n[None, :] < row_lens[:, None]) & n_mask[None, :]
        qk = tl.where(mask, qk, -float("inf"))
        
        # Softmax update
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        # Accumulate Output
        offs_dv = tl.arange(0, BLOCK_DV)
        v_ptrs = V_ptr + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < Dv), other=0.0)
        
        acc = acc * alpha[:, None]
        # p is float32, v is float16. Convert p to float16 for tensor cores
        acc += tl.dot(p.to(tl.float16), v)
        
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_new

    # Finalize
    # If l_i is 0 (no valid keys), output 0
    out = tl.where(l_i[:, None] > 0.0, acc / l_i[:, None], 0.0)
    
    offs_om = offs_m
    offs_od = tl.arange(0, BLOCK_DV)
    out_ptrs = Out_ptr + (offs_om[:, None] * stride_om + offs_od[None, :] * stride_od)
    tl.store(out_ptrs, out.to(tl.float16), mask=m_mask[:, None] & (offs_od[None, :] < Dv))

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Ensure row_lens is int32
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    def next_pow2(x):
        return 1 << (x - 1).bit_length()
    
    # Block sizes for dimensions
    BLOCK_D = max(16, next_pow2(D))
    BLOCK_DV = max(16, next_pow2(Dv))
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        sm_scale,
        BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV
    )
    
    return O
"""
        }
