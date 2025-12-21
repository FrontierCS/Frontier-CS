import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_attn_kernel(
    Q, K, V, RowLens, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    stride_lens,
    M, N,
    sm_scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Mask for M
    mask_m = offs_m < M

    # Load row_lens
    off_lens = offs_m * stride_lens
    row_lens = tl.load(RowLens + off_lens, mask=mask_m, other=0)
    
    # Load Q
    offs_d = tl.arange(0, BLOCK_D)
    off_q = offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(Q + off_q, mask=mask_m[:, None], other=0.0)
    q = q * sm_scale

    # Initialize accumulators
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    offs_n_base = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Loop over K blocks
    for start_n in range(0, N, BLOCK_N):
        cols = start_n + offs_n_base
        mask_n = cols < N
        
        # Load K
        off_k = cols[None, :] * stride_kn + offs_d[:, None] * stride_kd
        k = tl.load(K + off_k, mask=mask_n[None, :], other=0.0)
        
        # Compute scores
        qk = tl.dot(q, k)
        
        # Apply masks
        # Mask 1: Global N boundary (redundant with mask_n but explicit for scores)
        # Mask 2: Ragged lengths
        is_valid = (cols[None, :] < row_lens[:, None]) & mask_n[None, :]
        qk = tl.where(is_valid, qk, float("-inf"))
        
        # Streaming Softmax
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        # Calculate alpha = exp(m_i - m_new)
        # Handle -inf case to avoid NaN
        diff = m_i - m_new
        diff = tl.where(m_new == float("-inf"), 0.0, diff)
        alpha = tl.exp(diff)
        
        # Calculate P = exp(qk - m_new)
        exp_arg = qk - m_new[:, None]
        # Avoid NaN if m_new is -inf
        exp_arg = tl.where(m_new[:, None] == float("-inf"), float("-inf"), exp_arg)
        p = tl.exp(exp_arg)
        
        # Update l_i
        row_sum_p = tl.sum(p, 1)
        l_i = l_i * alpha + row_sum_p
        
        # Load V
        off_v = cols[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(V + off_v, mask=mask_n[:, None], other=0.0)
        
        # Accumulate
        p = p.to(tl.float16)
        pv = tl.dot(p, v)
        acc = acc * alpha[:, None] + pv
        
        m_i = m_new

    # Finalize
    # Out = acc / l_i
    # Handle l_i == 0 (rows with 0 length or all masked)
    out = acc / l_i[:, None]
    out = tl.where(l_i[:, None] == 0.0, 0.0, out)
    
    # Store
    off_o = offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(Out + off_o, out.to(tl.float16), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Ensure row_lens is int32
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
        
    O = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), )
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        row_lens.stride(0),
        M, N,
        sm_scale,
        BLOCK_D=D,
        BLOCK_DV=Dv
    )
    
    return O
"""
        return {"code": code}
