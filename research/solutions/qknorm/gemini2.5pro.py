import torch
import triton
import triton.language as tl
import flashinfer


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_D': 64}),
        triton.Config({'BLOCK_SIZE_D': 128}),
        triton.Config({'BLOCK_SIZE_D': 256}),
        triton.Config({'BLOCK_SIZE_D': 512}),
        triton.Config({'BLOCK_SIZE_D': 1024}),
    ],
    key=['D'],
)
@triton.jit
def _qknorm_kernel(
    # Pointers to tensors
    Q_ptr, K_ptr, Weight_ptr, Q_out_ptr, K_out_ptr,
    # Stride variables
    stride_q_row, stride_k_row,
    stride_q_d, stride_k_d,
    stride_w_d,
    stride_q_out_row, stride_k_out_row,
    stride_q_out_d, stride_k_out_d,
    # Other parameters
    num_q_tokens,
    D,
    eps,
    # Meta-parameters
    BLOCK_SIZE_D: tl.constexpr,
):
    """
    Triton kernel to apply RMSNorm to Q and K tensors in a single launch.
    This kernel is launched with a 1D grid where each program processes one token (row).
    It handles both Q and K tokens by branching based on the program ID.
    Strides are used to handle non-contiguous memory layouts efficiently.
    """
    # Get the program ID for the current token
    pid = tl.program_id(0)

    # Branch to handle either a Q or a K token
    if pid < num_q_tokens:
        in_ptr_row_base = Q_ptr + pid * stride_q_row
        out_ptr_row_base = Q_out_ptr + pid * stride_q_out_row
        in_d_stride = stride_q_d
        out_d_stride = stride_q_out_d
    else:
        # Adjust pid for K tensor
        pid_k = pid - num_q_tokens
        in_ptr_row_base = K_ptr + pid_k * stride_k_row
        out_ptr_row_base = K_out_ptr + pid_k * stride_k_out_row
        in_d_stride = stride_k_d
        out_d_stride = stride_k_out_d

    # --- RMSNorm computation for the selected row ---

    # Pointers to the elements of the current row
    d_offsets = tl.arange(0, BLOCK_SIZE_D)
    d_mask = d_offsets < D

    in_ptrs = in_ptr_row_base + d_offsets * in_d_stride

    # Load the row, converting to float32 for high-precision accumulation
    x = tl.load(in_ptrs, mask=d_mask, other=0.0).to(tl.float32)

    # Compute variance
    variance = tl.sum(x * x, axis=0) / D
    # Compute reciprocal standard deviation
    rstd = tl.math.rsqrt(variance + eps)

    # Load weights
    weight_ptrs = Weight_ptr + d_offsets * stride_w_d
    w = tl.load(weight_ptrs, mask=d_mask)

    # Apply normalization and weights
    # Cast back to original dtype before multiplying by weights
    normalized_x = (x * rstd).to(w.dtype)
    output = normalized_x * w

    # Write the result back to memory
    out_ptrs = out_ptr_row_base + d_offsets * out_d_stride
    tl.store(out_ptrs, output, mask=d_mask)


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using a single fused Triton kernel.

    This implementation fuses the normalization of Q and K into a single kernel
    launch to reduce overhead, which is critical for small, memory-bound
    operators. It handles non-contiguous tensors efficiently by passing strides
    to the kernel, avoiding explicit memory copies (e.g., .contiguous()).

    Args:
        q: Query tensor of arbitrary shape.
        k: Key tensor of arbitrary shape.
        norm_weight: Normalization weight tensor of shape (hidden_dim,).

    Returns:
        Tuple of (q_normalized, k_normalized) tensors.
    """
    # Preserve original shapes for the final output
    hidden_dim = q.shape[-1]

    # Reshape inputs to 2D (num_tokens, hidden_dim) to simplify kernel logic.
    # .reshape() is used as it can handle non-contiguous tensors without copying.
    q_2d = q.reshape(-1, hidden_dim)
    k_2d = k.reshape(-1, hidden_dim)

    num_q_tokens = q_2d.shape[0]
    total_tokens = num_q_tokens + k_2d.shape[0]

    # Handle empty inputs
    if total_tokens == 0:
        return torch.empty_like(q), torch.empty_like(k)

    # Allocate output tensors. Using empty_like preserves layout and device.
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    # Reshape output tensors to 2D to get correct strides for the kernel
    q_o_2d = q_o.reshape(-1, hidden_dim)
    k_o_2d = k_o.reshape(-1, hidden_dim)

    # Use a standard epsilon for RMSNorm, matching flashinfer's default.
    eps = 1e-6

    # Grid for the kernel is 1D, with one program per token
    grid = (total_tokens,)

    # Get strides. Handle the case of a 1-element tensor where stride can be 0.
    stride_w_d = norm_weight.stride(0) if norm_weight.numel() > 1 else 0

    # Launch the fused Triton kernel
    _qknorm_kernel[grid](
        q, k, norm_weight, q_o, k_o,
        q_2d.stride(0), k_2d.stride(0),
        q_2d.stride(1), k_2d.stride(1),
        stride_w_d,
        q_o_2d.stride(0), k_o_2d.stride(0),
        q_o_2d.stride(1), k_o_2d.stride(1),
        num_q_tokens,
        hidden_dim,
        eps,
        D=hidden_dim,  # Pass D as a key for autotuning
    )

    # The kernel modifies q_o and k_o in place, which have the correct final shape.
    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        import textwrap
        
        # Get the source code of the qknorm and _qknorm_kernel functions
        qknorm_source = inspect.getsource(qknorm)
        kernel_source = inspect.getsource(_qknorm_kernel)
        
        # Combine them into a single code string with necessary imports
        full_code = f"""
import torch
import triton
import triton.language as tl
import flashinfer

{textwrap.dedent(kernel_source)}
{textwrap.dedent(qknorm_source)}
"""
        return {"code": full_code.strip()}