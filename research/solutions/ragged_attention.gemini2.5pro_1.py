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

# This kernel is adapted from the Triton flash attention tutorial
# and has been specifically modified to handle ragged attention, where each
# query attends to a variable number of keys.

@triton.autotune(
    configs=[
        # A range of configurations for BLOCK_N and num_warps to find the optimal one.
        triton.Config({'BLOCK_N': 32}, num_warps=2),
        triton.Config({'BLOCK_N': 32}, num_warps=4),
        triton.Config({'BLOCK_N': 64}, num_warps=2),
        triton.Config({'BLOCK_N': 64}, num_warps=4),
        triton.Config({'BLOCK_N': 64}, num_warps=8),
        triton.Config({'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_N': 128}, num_warps=8),
        triton.Config({'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_warps=8),
    ],
    # Autotuning is keyed on matrix dimensions that affect performance.
    key=['D', 'Dv', 'N'],
)
@triton.jit
def _ragged_kernel(
    # Pointers to input/output tensors
    Q, K, V, O,
    ROW_LENS,
    # Strides for tensor access
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vdv,
    stride_om, stride_odv,
    stride_rl,
    # Matrix dimensions
    D, Dv, N,
    # Tiling constants, determined by autotuner or passed by host
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_D_V: tl.constexpr,
):
    \"\"\"
    Triton kernel for ragged attention.
    Each program instance computes one row of the output matrix O.
    The grid is 1D, with size M (number of queries).
    \"\"\"
    # Each program computes a single row of O. pid_m is the query index.
    pid_m = tl.program_id(axis=0)

    # Pointers to the current row for Q, O, and the specific row_len
    q_ptr = Q + pid_m * stride_qm
    o_ptr = O + pid_m * stride_om
    row_len_ptr = ROW_LENS + pid_m * stride_rl

    # Load the row length for this specific query. This is the "ragged" part.
    row_len = tl.load(row_len_ptr)

    # Initialize accumulator for the output and statistics for streaming softmax
    # Accumulation is done in float32 for numerical stability.
    acc = tl.zeros([BLOCK_D_V], dtype=tl.float32)
    m_i = -float('inf')
    l_i = 0.0
    
    # Standard attention scaling factor
    scale = (D) ** -0.5

    # Load the entire query vector for the current row.
    # This is efficient because D is small (64) and it can be reused for all key blocks.
    q_offsets = tl.arange(0, BLOCK_D)
    q = tl.load(q_ptr + q_offsets).to(tl.float32)

    # Loop over the key/value sequence in blocks of size BLOCK_N
    # The loop's upper bound is `row_len`, not the full N, which is the core
    # optimization for ragged inputs.
    for start_n in range(0, row_len, BLOCK_N):
        # --- 1. Compute attention scores S = Q @ K^T ---
        
        # Current block of key/value indices
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Pointers to the current block of keys
        k_offsets = offs_n[:, None] * stride_kn + q_offsets[None, :]
        
        # Mask to handle keys that are outside the valid `row_len`
        # This is crucial for correctness in the last block of a row.
        mask_n = offs_n < row_len
        
        # Load a block of keys, applying the mask to avoid out-of-bounds reads.
        k = tl.load(K + k_offsets, mask=mask_n[:, None], other=0.0).to(tl.float32)
        
        # Compute scores for the block: s = q @ k.T
        s = tl.sum(q[None, :] * k, axis=1) * scale
        
        # Apply the mask to scores, setting scores for padding to -inf.
        s = tl.where(mask_n, s, -float('inf'))

        # --- 2. Update softmax & accumulator (streaming) ---
        
        # Find the new maximum score for stable softmax calculation
        m_i_new = tl.maximum(m_i, tl.max(s, axis=0))
        
        # Compute probabilities with the new max for stability
        p = tl.exp(s - m_i_new)
        
        # Rescale the running sum of exponentiated scores
        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + tl.sum(p, axis=0)
        
        # Rescale the accumulator
        acc = acc * alpha
        
        # Load the corresponding block of values
        v_offsets = offs_n[:, None] * stride_vn + tl.arange(0, BLOCK_D_V)[None, :]
        v = tl.load(V + v_offsets, mask=mask_n[:, None], other=0.0)
        
        # Update accumulator with weighted values: acc += P @ V
        acc += tl.sum(p[:, None] * v.to(tl.float32), axis=0)
        
        # Update the max score for the next iteration
        m_i = m_i_new

    # --- 3. Finalize and store the output ---
    
    # Normalize the accumulator to get the final output vector
    # A safe division is used to handle cases where row_len is 0 (l_i=0).
    acc = tl.where(l_i > 0, acc / l_i, 0.0)
    
    # Pointers to the output row
    o_offsets = tl.arange(0, BLOCK_D_V)
    
    # Store the result, converting back to the output dtype (float16)
    tl.store(o_ptr + o_offsets, acc.to(O.dtype.element_ty))


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
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)

    # The grid is 1D, with one program instance per query row.
    grid = (M,)
    
    # Triton kernels generally require int32 indices.
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
        
    # Launch the Triton kernel.
    _ragged_kernel[grid](
        # Tensors
        Q, K, V, O, row_lens,
        # Strides
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        row_lens.stride(0),
        # Dimensions
        D, Dv, N,
        # Kernel constants
        # Specialize kernel for D and Dv values from the problem statement.
        # This allows the compiler to produce more efficient code by unrolling loops.
        BLOCK_D=D,
        BLOCK_D_V=Dv
    )
    
    return O
"""
        return {"code": code}