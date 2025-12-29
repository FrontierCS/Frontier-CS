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
        triton.Config({'BLOCK_N': 32}, num_warps=2),
        triton.Config({'BLOCK_N': 64}, num_warps=2),
        triton.Config({'BLOCK_N': 64}, num_warps=4),
        triton.Config({'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_warps=8),
        triton.Config({'BLOCK_N': 512}, num_warps=8),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_kernel(
    Q, K, V, O,
    row_lens,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    # Each program instance computes one row of the output.
    pid_m = tl.program_id(axis=0)

    # Load the q vector for the current row. This is a single vector.
    q_offs = pid_m * stride_qm + tl.arange(0, BLOCK_D)
    q = tl.load(Q + q_offs)
    
    # Load the specific row length for this query. This is the core of ragged attention.
    current_row_len = tl.load(row_lens + pid_m)

    # Initialize accumulator for the output, and statistics for streaming softmax.
    # Accumulation is done in float32 for numerical stability.
    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)
    m_i = -float("inf")
    l_i = 0.0
    scale = (D ** -0.5)

    # Loop over blocks of keys and values along the sequence length N.
    offs_n_block = tl.arange(0, BLOCK_N)
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        current_n_base = start_n * BLOCK_N
        # Optimization: if the start of this block is already past the valid row length,
        # we can skip all subsequent blocks.
        if current_n_base >= current_row_len:
            break

        # --- Load a block of keys (K) ---
        offs_d = tl.arange(0, BLOCK_D)
        offs_n = current_n_base + offs_n_block
        k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        
        # Mask for keys that are within the valid row length.
        k_mask = (offs_n < current_row_len)
        # Load keys, masking out-of-bounds elements to 0.
        k = tl.load(k_ptrs, mask=k_mask[:, None], other=0.0)

        # --- Compute attention scores (S = Q @ K^T) ---
        # tl.dot for fp16 inputs uses fp32 accumulation internally for precision.
        s = tl.dot(q[None, :], tl.trans(k))
        s *= scale
        
        # Apply the ragged mask to scores, setting scores for padding tokens to -inf.
        # This is crucial for correct softmax computation.
        s = tl.where(k_mask[None, :], s, -float("inf"))

        # --- Streaming softmax update ---
        # This computes softmax in a single pass, which is numerically stable.
        m_i_new = tl.maximum(m_i, tl.max(s, axis=1))
        p = tl.exp(s - m_i_new)
        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + tl.sum(p, axis=1)

        # --- Load a block of values (V) ---
        offs_dv = tl.arange(0, BLOCK_DV)
        v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        # Use the same mask as for K to load values.
        v = tl.load(v_ptrs, mask=k_mask[:, None], other=0.0)

        # --- Update the output accumulator (O) ---
        # Rescale the accumulator and add the new weighted values.
        acc = acc * alpha
        p = p.to(V.dtype.element_ty) # Cast probabilities to fp16 for the dot product.
        acc_update = tl.dot(p, v)
        acc += tl.view(acc_update, [BLOCK_DV])
        
        m_i = m_i_new
        
    # --- Finalize and store the output ---
    # Normalize the accumulator by the total sum of probabilities.
    # Add a small epsilon to l_i to avoid division by zero for empty sequences.
    l_i = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i
    
    # Store the final result, casting back to float16.
    o_offs = pid_m * stride_om + tl.arange(0, BLOCK_DV)
    tl.store(O + o_offs, acc.to(O.dtype.element_ty))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Allocate the output tensor.
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    # The grid defines the number of program instances to launch.
    # Here, we launch one program per query row.
    grid = (M,)
    
    # Launch the Triton kernel.
    _ragged_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        BLOCK_D=D,
        BLOCK_DV=Dv
    )
    
    return O
"""
        return {"code": code}