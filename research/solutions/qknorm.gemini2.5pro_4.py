import torch
import triton
import triton.language as tl
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict containing the Python code for the qknorm implementation.
        """
        qknorm_code = """
import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_kernel(
    # Pointers to matrices
    Q_ptr, K_ptr, W_ptr, Q_out_ptr, K_out_ptr,
    # Matrix dimensions
    q_num_rows, D,
    # Strides for row-major access
    q_stride_rm, k_stride_rm,
    q_out_stride_rm, k_out_stride_rm,
    # Meta-parameters
    eps,
    # Compiler constants
    BLOCK_SIZE_D: tl.constexpr,
):
    \"\"\"
    Fused Triton kernel for applying RMSNorm to Q and K tensors.
    \"\"\"
    # Each program in the grid processes one row of the combined Q and K tensors.
    row_idx = tl.program_id(0)

    # Determine if we are processing a row from Q or K and set up the
    # corresponding pointers and strides. This branch is resolved at compile time.
    if row_idx < q_num_rows:
        # This row belongs to the Q tensor
        in_ptr = Q_ptr + row_idx * q_stride_rm
        out_ptr = Q_out_ptr + row_idx * q_out_stride_rm
    else:
        # This row belongs to the K tensor
        k_row_idx = row_idx - q_num_rows
        in_ptr = K_ptr + k_row_idx * k_stride_rm
        out_ptr = K_out_ptr + k_row_idx * k_out_stride_rm

    # --- RMSNorm Computation ---
    
    # Define column offsets for the feature dimension.
    col_offsets = tl.arange(0, BLOCK_SIZE_D)
    mask = col_offsets < D
    
    # Load the row. Masking handles cases where D is not a multiple of BLOCK_SIZE_D.
    # The row is cast to float32 for numerically stable accumulation.
    row = tl.load(in_ptr + col_offsets, mask=mask, other=0.0).to(tl.float32)
    
    # Compute the variance (mean of squares).
    variance = tl.sum(row * row, axis=0) / D
    # Compute the reciprocal of the standard deviation.
    rstd = tl.math.rsqrt(variance + eps)
    
    # Load the corresponding weights.
    weights = tl.load(W_ptr + col_offsets, mask=mask)
    
    # Apply the normalization: y = x * rstd * w.
    normed_row = row * rstd * weights
    
    # Store the result back to the output tensor.
    # The cast to the output tensor's dtype is handled automatically by tl.store.
    tl.store(out_ptr + col_offsets, normed_row, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    \"\"\"
    Apply RMSNorm to query and key tensors using a single fused Triton kernel.
    
    This implementation fuses the normalization of Q and K into a single kernel
    launch, significantly reducing overhead for this small, launch-bound operator.
    It efficiently handles non-contiguous inputs by operating on strides, thus
    avoiding explicit and costly .contiguous() calls. A fallback to the baseline
    flashinfer implementation is included for edge cases with non-contiguous feature
    dimensions to ensure correctness, adhering to the problem's primary goal.

    Args:
        q: Query tensor of arbitrary shape.
        k: Key tensor of arbitrary shape.
        norm_weight: Normalization weight tensor of shape (hidden_dim,).
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors.
    \"\"\"
    # Get original shapes and the hidden dimension.
    q_shape = q.shape
    hidden_dim = q_shape[-1]
    
    # Validate that the feature dimension is consistent across all tensors.
    if k.shape[-1] != hidden_dim or norm_weight.shape[0] != hidden_dim:
        raise ValueError("The last dimension of q, k, and norm_weight must be the same.")

    # Logically reshape inputs to 2D. This is a metadata-only operation
    # (no data copy) if the tensor layout allows for it.
    q_2d = q.reshape(-1, hidden_dim)
    k_2d = k.reshape(-1, hidden_dim)

    # Our Triton kernel is optimized for the common case where the feature dimension
    # is contiguous in memory (stride=1), which enables fast vectorized memory access.
    # If this is not the case, we fall back to the baseline implementation, which uses
    # two separate flashinfer calls, to guarantee correctness under all circumstances.
    if q_2d.stride(1) != 1 or k_2d.stride(1) != 1 or norm_weight.stride(0) != 1:
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    # Allocate output tensors, preserving the memory layout of the inputs.
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)
    
    # Reshape output tensors for the kernel interface.
    q_o_2d = q_o.reshape(-1, hidden_dim)
    k_o_2d = k_o.reshape(-1, hidden_dim)

    # Set up kernel launch parameters.
    q_num_rows = q_2d.shape[0]
    total_rows = q_num_rows + k_2d.shape[0]
    
    # Handle empty input tensors.
    if total_rows == 0:
        return q_o, k_o
        
    # The grid is 1D, with one program launched per row of the combined Q and K tensors.
    grid = (total_rows,)
    
    # Use a common Triton heuristic: set block size to the next power of 2.
    BLOCK_SIZE_D = triton.next_power_of_2(hidden_dim)
    
    _qknorm_kernel[grid](
        # Tensors
        q_2d, k_2d, norm_weight, q_o_2d, k_o_2d,
        # Dimensions
        q_num_rows, hidden_dim,
        # Strides for row-major access
        q_2d.stride(0), k_2d.stride(0),
        q_o_2d.stride(0), k_o_2d.stride(0),
        # Meta-parameters
        eps=1e-6,
        # Triton constants
        BLOCK_SIZE_D=BLOCK_SIZE_D,
    )
    
    # Return the output tensors. They are already in their correct original shapes
    # due to being allocated with `empty_like(q)` and `empty_like(k)`.
    return q_o, k_o
"""
        return {"code": qknorm_code}