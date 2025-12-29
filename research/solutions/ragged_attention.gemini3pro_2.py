import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
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
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Grid handling for M
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Load row_lens for masking
    # row_lens shape (M,)
    rl_val = tl.load(RowLens + offs_m, mask=mask_m, other=0)
    
    offs_d = tl.arange(0, BLOCK_D)
    
    # Load Q: (BLOCK_M, BLOCK_D)
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Initialize accumulators
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Base pointers for K and V
    # K: (N, D), V: (N, Dv)
    k_base = K + offs_d[None, :] * stride_kd
    v_base = V + offs_dv[None, :] * stride_vd
    
    # Loop over N blocks
    for start_n in range(0, N, BLOCK_N):
        cols = start_n + offs_n
        mask_n = cols < N
        
        # Load K block: (BLOCK_N, BLOCK_D)
        k_ptrs = k_base + cols[:, None] * stride_kn
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute scores: Q (BM, D) @ K.T (D, BN) -> (BM, BN)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Ragged Masking: check if column index < row_len for each query
        mask_ragged = cols[None, :] < rl_val[:, None]
        # Combine with valid N mask
        mask_op = mask_ragged & mask_n[None, :]
        
        # Apply mask
        qk = tl.where(mask_op, qk, float("-inf"))
        
        # Streaming Softmax
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        p = tl.exp(qk - m_new[:, None])
        alpha = tl.exp(m_i - m_new)
        
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_new
        
        # Load V block: (BLOCK_N, BLOCK_DV)
        v_ptrs = v_base + cols[:, None] * stride_vn
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Accumulate: P (BM, BN) @ V (BN, BDV) -> (BM, BDV)
        # Cast P to float16 for mixed precision dot product
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
    
    # Normalize and Store Output
    out = acc / l_i[:, None]
    out_ptrs = Out + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(out_ptrs, out.to(tl.float16), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Prepare output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        M, N,
        BLOCK_D=D, BLOCK_DV=Dv
    )
    
    return O