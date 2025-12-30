import torch
import triton
import triton.language as tl
import inspect

# It is required to have a `qknorm` function in the global scope.
# The `Solution` class will return the source code of this file.

@triton.jit
def _qknorm_kernel(
    # Pointers to Tensors
    Q_ptr, K_ptr, W_ptr, Q_out_ptr, K_out_ptr,
    # Dimensions
    num_q_rows, D,
    # Strides
    q_stride_0, q_stride_1,
    k_stride_0, k_stride_1,
    w_stride_0,
    q_out_stride_0, q_out_stride_1,
    k_out_stride_0, k_out_stride_1,
    # Constants
    eps: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    """
    Fused Triton kernel for RMS Normalization on Q and K tensors.

    This kernel processes one row of either Q or K per program instance.
    The grid is launched over the total number of rows (tokens) in Q and K combined.
    A simple dispatch logic (`if pid < num_q_rows`) directs each program to the
    correct input (Q or K) and output (Q_out or K_out) tensor.

    This fusion reduces two separate kernel launches into one, significantly cutting
    down on launch overhead, which is a major bottleneck for such small, memory-bound
    operations. The use of strides allows the kernel to efficiently handle
    non-contiguous tensor layouts without requiring extra memory copies.
    """
    # Each program instance processes one row from the combined Q and K tensors
    pid = tl.program_id(axis=0)

    # Dispatch logic: decide whether to process from Q or K based on program ID
    is_q = pid < num_q_rows
    if is_q:
        row_idx = pid
        X_ptr = Q_ptr + row_idx * q_stride_0
        X_out_ptr = Q_out_ptr + row_idx * q_out_stride_0
        x_stride_1 = q_stride_1
        x_out_stride_1 = q_out_stride_1
    else:
        row_idx = pid - num_q_rows
        X_ptr = K_ptr + row_idx * k_stride_0
        X_out_ptr = K_out_ptr + row_idx * k_out_stride_0
        x_stride_1 = k_stride_1
        x_out_stride_1 = k_out_stride_1

    # Define column offsets for vectorized memory access
    d_offsets = tl.arange(0, BLOCK_D)
    mask = d_offsets < D

    # === Pass 1: Compute variance ===
    # Load a row of data. Using strides handles non-contiguous inputs efficiently.
    # All computations are promoted to float32 for numerical stability and precision.
    x_ptrs = X_ptr + d_offsets * x_stride_1
    x = tl.load(x_ptrs, mask=mask, other=0.0).to(tl.float32)

    # Compute sum of squares for RMSNorm
    sum_sq = tl.sum(x * x, axis=0)
    var = sum_sq / D
    rstd = tl.math.rsqrt(var + eps)

    # === Pass 2: Normalize, apply weights, and store ===
    # Load the corresponding weights
    w_ptrs = W_ptr + d_offsets * w_stride_0
    w = tl.load(w_ptrs, mask=mask, other=0.0).to(tl.float32)

    # Normalize the input row and apply the weights in float32
    output = x * rstd * w

    # Store the result. Triton handles the cast from float32 back to the output tensor's dtype.
    x_out_ptrs = X_out_ptr + d_offsets * x_out_stride_1
    tl.store(x_out_ptrs, output, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using a single fused Triton kernel.

    This implementation fuses the two separate normalization operations into a single
    kernel launch, which is crucial for performance in launch-bound scenarios.
    It handles arbitrary tensor shapes and non-contiguous memory layouts without
    incurring extra data copies.

    Args:
        q: Query tensor of arbitrary shape (will be reshaped to 2D)
        k: Key tensor of arbitrary shape (will be reshaped to 2D)
        norm_weight: Normalization weight tensor of shape (hidden_dim,)

    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    # Preserve original shapes to correctly reshape the outputs at the end
    q_shape, k_shape = q.shape, k.shape
    hidden_dim = q.shape[-1]

    # Reshape Q and K to 2D views: (num_tokens, hidden_dim).
    # Using .reshape() is safer than .view() as it can handle more
    # non-contiguous cases without raising an error.
    q_2d = q.reshape(-1, hidden_dim)
    k_2d = k.reshape(-1, hidden_dim)

    num_q_rows = q_2d.shape[0]
    total_rows = num_q_rows + k_2d.shape[0]

    # Pre-allocate output tensors with the same 2D shape as the inputs
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)

    # The grid is 1D, launching one program per row of Q and K combined.
    grid = (total_rows,)

    # Heuristic for block size: smallest power of 2 >= hidden_dim.
    # This ensures the entire row is processed in a single vectorized step
    # within the kernel, maximizing memory throughput.
    BLOCK_D = triton.next_power_of_2(hidden_dim)

    # Heuristic for the number of warps, which can affect occupancy and performance.
    num_warps = 4
    if BLOCK_D >= 2048:
        num_warps = 8
    if BLOCK_D >= 4096:
        num_warps = 16

    # Launch the fused Triton kernel
    _qknorm_kernel[grid](
        q_2d, k_2d, norm_weight, q_o, k_o,
        num_q_rows, hidden_dim,
        # Strides are passed explicitly to handle any memory layout
        q_2d.stride(0), q_2d.stride(1),
        k_2d.stride(0), k_2d.stride(1),
        norm_weight.stride(0),
        q_o.stride(0), q_o.stride(1),
        k_o.stride(0), k_o.stride(1),
        eps=1e-6,  # Standard epsilon for RMSNorm
        BLOCK_D=BLOCK_D,
        num_warps=num_warps,
    )

    # Reshape the 2D outputs back to their original, potentially multi-dimensional, shapes
    return q_o.reshape(q_shape), k_o.reshape(k_shape)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict containing the Python code for the QKNorm implementation.
        """
        # Get the source code of all necessary components
        # The 'flashinfer' import is included to match the problem specification context,
        # even though the custom Triton kernel is used instead of flashinfer.norm.rmsnorm
        # to achieve the required kernel fusion for performance.
        kernel_source = inspect.getsource(_qknorm_kernel)
        qknorm_source = inspect.getsource(qknorm)
        
        # Combine into a single string for the solution
        code_string = f"""
import torch
import triton
import triton.language as tl
import flashinfer

{kernel_source}

{qknorm_source}
"""
        return {"code": code_string}