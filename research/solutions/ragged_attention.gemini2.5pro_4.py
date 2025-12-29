import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_kernel(
    Q, K, V, O,
    ROW_LENS,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vdv,
    stride_om, stride_odv,
    M, N, D, Dv,
    # These are fixed for this problem, so they are compile-time constants
    BLOCK_D: tl.constexpr, 
    BLOCK_DV: tl.constexpr,
    # These are tuned by autotuner, so they are also compile-time constants
    BLOCK_M: tl.constexpr, 
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)

    # offsets for the M dimension (query rows)
    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = m_offsets < M

    # load row lengths for the current block of queries
    row_lens_ptrs = ROW_LENS + m_offsets
    current_row_lens = tl.load(row_lens_ptrs, mask=m_mask, other=0)

    # initialize pointers to Q and load the block of Q
    # this block of Q will be reused for all blocks of K and V
    d_offsets = tl.arange(0, BLOCK_D)
    q_ptrs = Q + m_offsets[:, None] * stride_qm + d_offsets[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None])

    # initialize accumulators for the streaming softmax
    # acc holds the output, l_i is the normalization factor, m_i is the max score
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)

    scale = (D ** -0.5)

    # loop over K and V in blocks of size BLOCK_N
    for start_n in range(0, N, BLOCK_N):
        # offsets for the N dimension (key/value rows)
        n_offsets = start_n + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N

        # load K
        k_ptrs = K + n_offsets[:, None] * stride_kn + d_offsets[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None])

        # compute attention scores
        # scores are accumulated in float32
        scores = tl.dot(q, tl.trans(k)) * scale
        
        # apply the ragged mask
        # this ensures each query row only attends to its specified number of keys
        ragged_mask = n_offsets[None, :] < current_row_lens[:, None]
        # set scores for masked-out elements to -inf
        scores = tl.where(ragged_mask, scores, -float('inf'))

        # --- streaming softmax update ---
        # 1. find the new max score for the row
        block_m_i = tl.max(scores, axis=1)
        new_m_i = tl.maximum(m_i, block_m_i)
        
        # 2. rescale previous accumulator and normalization factor
        exp_diff = tl.exp(m_i - new_m_i)
        
        # 3. compute probabilities for the current block
        p = tl.exp(scores - new_m_i[:, None])
        
        # 4. update normalization factor and accumulator
        l_i = l_i * exp_diff + tl.sum(p, axis=1)
        acc = acc * exp_diff[:, None]
        
        # 5. update max score
        m_i = new_m_i
        
        # load V
        dv_offsets = tl.arange(0, BLOCK_DV)
        v_ptrs = V + n_offsets[:, None] * stride_vn + dv_offsets[None, :] * stride_vdv
        v = tl.load(v_ptrs, mask=n_mask[:, None])

        # update output accumulator
        p = p.to(v.dtype) # cast probabilities to float16 for matmul
        acc += tl.dot(p, v)

    # finalize the output by dividing by the normalization factor
    # handle case where l_i is 0 (e.g., row_len is 0) to avoid NaN
    l_i_safe = tl.where(l_i == 0, 1, l_i)
    acc = acc / l_i_safe[:, None]

    # write the output block to global memory
    dv_offsets = tl.arange(0, BLOCK_DV)
    o_ptrs = O + m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_odv
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=m_mask[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape

    # Assertions for correctness
    assert D == D_k, "Query and Key dimensions must match"
    assert N == N_v, "Key and Value sequence lengths must match"
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16

    # Allocate output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)

    # Grid definition
    # The grid is 1D, with one program per BLOCK_M rows of Q.
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    # Kernel dimensions are fixed in the problem statement
    BLOCK_D = 64
    BLOCK_DV = 64

    # Launch the kernel
    _ragged_kernel[grid](
        Q, K, V, O,
        row_lens,
        # Strides
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        # Matrix dimensions
        M, N, D, Dv,
        # Compile-time constants
        BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
    )
    return O
"""
        return {"code": code}