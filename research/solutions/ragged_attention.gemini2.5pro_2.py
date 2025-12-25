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
        
        ragged_attn_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 32}, num_warps=2, num_stages=3),
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=3),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=3),
        # configs with more stages for better pipelining
        triton.Config({'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=4),
    ],
    key=['N', 'D', 'DV'],
)
@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O,
    ROW_LENS,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vdv,
    stride_om, stride_odv,
    M, N,
    D: tl.constexpr,
    DV: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # Each program instance computes one row of the output.
    pid_m = tl.program_id(axis=0)

    # Load the row length for the current query. This is the core of "ragged" attention.
    current_row_len = tl.load(ROW_LENS + pid_m)

    # Pointers to the current query row. D is assumed to be small enough to be loaded at once.
    q_offs = pid_m * stride_qm + tl.arange(0, D)
    q = tl.load(Q + q_offs)

    # Initialize accumulators for streaming softmax and the output.
    # m_i: current maximum score, l_i: current sum of exp(score - m_i), acc: output accumulator
    m_i = -float('inf')
    l_i = 0.0
    acc = tl.zeros([DV], dtype=tl.float32)
    
    scale = (D ** -0.5)

    # Loop over K and V in blocks of size BLOCK_N.
    # The loop bound is determined by the full size of N, and masking is handled inside.
    for block_idx in range(0, tl.cdiv(N, BLOCK_N)):
        start_n = block_idx * BLOCK_N
        
        # --- 1. Compute attention scores S = Q @ K.T ---
        
        # Load a block of K.
        k_offs = (start_n + tl.arange(0, BLOCK_N))[:, None] * stride_kn + tl.arange(0, D)[None, :]
        # Boundary check for the last block of K.
        k_mask = (start_n + tl.arange(0, BLOCK_N)) < N
        k = tl.load(K + k_offs, mask=k_mask[:, None], other=0.0)
        
        # Compute scores. The dot product is done in float32 for precision.
        s = tl.dot(q, tl.trans(k)) * scale
        
        # --- 2. Apply ragged mask ---
        # Mask out scores where the column index `j` is >= `current_row_len`.
        col_indices = start_n + tl.arange(0, BLOCK_N)
        ragged_mask = col_indices < current_row_len
        s = tl.where(ragged_mask, s, -float('inf'))

        # --- 3. Update streaming softmax statistics (online softmax) ---
        m_i_new = tl.maximum(m_i, tl.max(s, axis=0))
        p = tl.exp(s - m_i_new)
        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + tl.sum(p, axis=0)

        # --- 4. Update output accumulator ---
        
        # Load the corresponding block of V.
        v_offs = (start_n + tl.arange(0, BLOCK_N))[:, None] * stride_vn + tl.arange(0, DV)[None, :]
        # Boundary check for the last block of V.
        v_mask = (start_n + tl.arange(0, BLOCK_N)) < N
        v = tl.load(V + v_offs, mask=v_mask[:, None], other=0.0)
        
        # Rescale the accumulator with the new max score.
        acc = acc * alpha
        
        # Add the contribution from the current block: p @ v
        # p is already masked because exp(-inf) = 0.
        # We use tl.dot for efficient hardware utilization (Tensor Cores).
        acc += tl.dot(p.to(V.dtype.element_ty), v)

        # Update the max score for the next iteration.
        m_i = m_i_new

    # --- 5. Finalize and store the output ---
    # Normalize the accumulator by the total sum l_i.
    acc = acc / l_i
    
    # Write the final output row.
    o_offs = pid_m * stride_om + tl.arange(0, DV)
    tl.store(O + o_offs, acc.to(O.dtype.element_ty))


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
    N, Dk = K.shape
    Nv, Dv = V.shape

    # Input validation
    assert D == Dk, "Query and Key dimensions must match"
    assert N == Nv, "Key and Value sequence lengths must match"
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert row_lens.dtype in [torch.int32, torch.int64]

    # Allocate output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)

    # Grid consists of M programs, one for each query row.
    grid = (M,)
    
    # Launch the Triton kernel.
    _ragged_attn_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N,
        D=D, DV=Dv,
    )

    return O
"""
        return {"code": ragged_attn_code}
