import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32}, num_stages=5, num_warps=2),
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
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    # Determine the program's position in the grid.
    pid_m = tl.program_id(0)

    # Compute offsets for the current block of queries.
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    # Compute offsets for the feature dimensions.
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Create pointers to the Q block.
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    
    # Create a mask to handle the case where M is not a multiple of BLOCK_M.
    m_mask = offs_m < M
    
    # Load the specific row lengths for the current block of queries.
    row_lens_ptrs = ROW_LENS + offs_m
    row_lens_m = tl.load(row_lens_ptrs, mask=m_mask, other=0)

    # Initialize accumulators for the output and statistics for streaming softmax.
    # Use float32 for higher precision.
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)

    # Attention scaling factor.
    scale = (D ** -0.5)

    # Load the Q block once and pre-scale it.
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
    q = (q * scale).to(q.dtype)

    # Main loop over the key/value sequence.
    for start_n in range(0, N, BLOCK_N):
        # Compute offsets for the current block of keys/values.
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Create pointers to the K and V blocks.
        k_ptrs = K + (offs_d[:, None] * stride_kd + offs_n[None, :] * stride_kn)
        v_ptrs = V + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vdv)
        
        # Create boundary masks for the N dimension to avoid out-of-bounds access.
        n_mask_k = offs_n[None, :] < N
        n_mask_v = offs_n[:, None] < N

        # Load K and V blocks from memory.
        k = tl.load(k_ptrs, mask=n_mask_k, other=0.0)
        v = tl.load(v_ptrs, mask=n_mask_v, other=0.0)
        
        # Compute attention scores.
        s = tl.dot(q, k, out_dtype=tl.float32)

        # Apply the ragged attention mask.
        # This is the core logic that handles variable sequence lengths.
        # It combines the M-boundary mask with the row-length specific mask.
        ragged_mask = m_mask[:, None] & (offs_n[None, :] < row_lens_m[:, None])
        s = tl.where(ragged_mask, s, -float('inf'))
        
        # --- Streaming softmax computation ---
        # Find the new maximum score for the current block.
        m_j = tl.max(s, 1)
        # Update the overall maximum score.
        m_new = tl.maximum(m_i, m_j)
        
        # Compute probabilities, rescaled with the new maximum for numerical stability.
        p = tl.exp(s - m_new[:, None])
        
        # Rescale the old accumulator and sum of probabilities (l_i).
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha[:, None]
        l_i = l_i * alpha
        
        # Update the sum of probabilities with the new block's sum.
        l_j = tl.sum(p, 1)
        l_i += l_j
        
        # Update the accumulator with the new values (P @ V).
        p = p.to(V.dtype.element_ty)
        acc += tl.dot(p, v)

        # Update the overall maximum for the next iteration.
        m_i = m_new

    # Final normalization step.
    # Protect against division by zero for rows with no valid keys.
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]
    
    # Create pointers to the output tensor O.
    o_ptrs = O + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_odv)
    
    # Store the final result.
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=m_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    \"\"\"
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape

    # Allocate the output tensor.
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    # Define the grid for launching the kernel. Each program handles a block of M.
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    # Launch the Triton kernel.
    _ragged_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        BLOCK_D=D, BLOCK_DV=Dv
    )

    return O
"""
        return {"code": code}
