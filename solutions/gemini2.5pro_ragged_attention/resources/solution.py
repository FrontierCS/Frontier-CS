import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BM': 64, 'BN': 64}, num_stages=4, num_warps=4),
        triton.Config({'BM': 128, 'BN': 64}, num_stages=3, num_warps=4),
        triton.Config({'BM': 64, 'BN': 128}, num_stages=3, num_warps=4),
        triton.Config({'BM': 128, 'BN': 128}, num_stages=2, num_warps=8),
        triton.Config({'BM': 64, 'BN': 64}, num_stages=3, num_warps=8),
        triton.Config({'BM': 32, 'BN': 128}, num_stages=2, num_warps=4),
        triton.Config({'BM': 128, 'BN': 32}, num_stages=2, num_warps=4),
        triton.Config({'BM': 32, 'BN': 64}, num_stages=4, num_warps=4),
        triton.Config({'BM': 64, 'BN': 32}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_kernel(
    Q, K, V, O,
    ROW_LENS,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    SCALE: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr, BD: tl.constexpr, BDV: tl.constexpr,
):
    # Each program instance computes a BM x BDV block of the output matrix O.
    pid_m = tl.program_id(0)

    # Offsets for the M dimension (queries).
    m_offsets = pid_m * BM + tl.arange(0, BM)
    m_mask = m_offsets < M

    # Pointers to Q, O, and ROW_LENS for the current block.
    # We multiply by stride_qd, stride_od, etc. to support non-contiguous tensors.
    q_ptrs = Q + m_offsets[:, None] * stride_qm + tl.arange(0, BD)[None, :] * stride_qd
    o_ptrs = O + m_offsets[:, None] * stride_om + tl.arange(0, BDV)[None, :] * stride_od
    row_lens_ptrs = ROW_LENS + m_offsets

    # Load row lengths for this block. This is the key component for ragged attention.
    row_lens = tl.load(row_lens_ptrs, mask=m_mask, other=0)

    # Initialize accumulator and online softmax statistics.
    acc = tl.zeros([BM, BDV], dtype=tl.float32)
    m_i = tl.full([BM], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BM], dtype=tl.float32)

    # Load Q block once. It will be reused across all K/V blocks.
    q = tl.load(q_ptrs, mask=m_mask[:, None])
    q = (q * SCALE).to(q.dtype)

    # Loop over K and V in blocks along the sequence length (N) dimension.
    for start_n in range(0, N, BN):
        # -- Load K and V blocks --
        n_offsets = start_n + tl.arange(0, BN)
        n_mask = n_offsets < N
        
        # Load K block (BN, BD) for Q @ K^T.
        k_ptrs = K + n_offsets[:, None] * stride_kn + tl.arange(0, BD)[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)
        
        # Load V block (BN, BDV).
        v_ptrs = V + n_offsets[:, None] * stride_vn + tl.arange(0, BDV)[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)

        # -- Compute scores S = Q @ K^T --
        # q is (BM, BD), k is (BN, BD). Use trans_b=True for Q @ K^T.
        s = tl.dot(q, k, trans_b=True)

        # -- Apply ragged mask --
        # The mask is True if the K element is within the sequence length for the Q row.
        ragged_mask = (n_offsets[None, :] < row_lens[:, None]) & m_mask[:, None]
        s = tl.where(ragged_mask, s, -float('inf'))

        # -- Online softmax update --
        # 1. Find new max for normalization.
        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        # 2. Compute P = exp(S - m_new) with safe exponentiation to prevent NaNs.
        is_m_new_neg_inf = (m_new == -float('inf'))
        s_shifted = s - m_new[:, None]
        s_shifted = tl.where(is_m_new_neg_inf[:, None], -float('inf'), s_shifted)
        p = tl.exp(s_shifted)
        p = tl.where(ragged_mask, p, 0.0)
        
        # 3. Compute scale factor for previous statistics: alpha = exp(m_i - m_new).
        is_m_i_neg_inf = (m_i == -float('inf'))
        m_i_safe = tl.where(is_m_i_neg_inf, m_new, m_i)
        alpha = tl.exp(m_i_safe - m_new)

        # 4. Update statistics.
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        # 5. Update accumulator.
        acc = acc * alpha[:, None]
        p_cast = p.to(v.dtype)
        acc += tl.dot(p_cast, v)

        m_i = m_new

    # Final normalization.
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]

    # Store output block.
    tl.store(o_ptrs, acc.to(o_ptrs.dtype.element_ty), mask=m_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, D_k = K.shape
    _, Dv = V.shape
    assert D == D_k, "Query and Key dimensions must match"
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"

    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)

    grid = lambda META: (triton.cdiv(M, META['BM']),)
    
    # Triton kernel expects int32 for row_lens for pointer arithmetic.
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    
    scale = D ** -0.5
    
    # Since D and Dv are fixed in this problem, we can pass them as compile-time constants.
    _ragged_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        SCALE=scale,
        BD=D, BDV=Dv
    )
    return O
"""
        return {"code": code}
