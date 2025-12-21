import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=16),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    BLOCK_SIZE_N: tl.constexpr,
):
    # Each program instance computes the loss for a single sample (row).
    pid_m = tl.program_id(0)

    # Pointer to the start of the current row in the logits tensor.
    row_logits_ptr = logits_ptr + pid_m * stride_logits_m

    # Use the online softmax algorithm for numerical stability.
    # This involves a single pass over the data, maintaining a running max
    # and a sum of exponentials, properly scaled.
    row_max = -float('inf')
    sum_exp = 0.0
    
    # Pre-calculate offsets for the vocabulary dimension.
    offsets_n = tl.arange(0, BLOCK_SIZE_N)
    
    # Iterate over the vocabulary dimension in blocks.
    for off in range(0, N, BLOCK_SIZE_N):
        # Calculate column indices for the current block.
        cols = off + offsets_n
        # Create a mask to handle the last block if N is not a multiple of BLOCK_SIZE_N.
        mask = cols < N

        # Load a block of logits, applying the mask.
        # Masked-out elements are set to -inf to not affect the max operation.
        x = tl.load(row_logits_ptr + cols * stride_logits_n, mask=mask, other=-float('inf'))

        # --- Online softmax update step ---
        # Find the maximum value in the current block.
        block_max = tl.max(x, axis=0)
        # Find the new overall maximum.
        new_max = tl.maximum(row_max, block_max)

        # Rescale the running sum of exponentials with the new maximum.
        # This prevents numerical overflow/underflow.
        sum_exp = sum_exp * tl.exp(row_max - new_max)
        # Compute exponentials for the current block, scaled by the new maximum.
        p = tl.exp(x - new_max)
        
        # Update the sum of exponentials and the running maximum.
        sum_exp += tl.sum(p, axis=0)
        row_max = new_max

    # After iterating through all blocks, compute the log-sum-exp.
    log_sum_exp = row_max + tl.log(sum_exp)

    # Load the target class index for the current row.
    target_idx = tl.load(targets_ptr + pid_m)
    # Load the logit value corresponding to the target index (scalar load).
    logit_target = tl.load(row_logits_ptr + target_idx * stride_logits_n)

    # Calculate the cross-entropy loss.
    loss = log_sum_exp - logit_target
    
    # Store the final loss value for the current row.
    tl.store(output_ptr + pid_m, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Cross entropy loss computation.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss for each sample
    \"\"\"
    M, N = logits.shape

    # Allocate the output tensor for the loss.
    loss = torch.empty((M,), dtype=torch.float32, device=logits.device)

    # The grid is 1D, with M programs, one for each sample in the batch.
    grid = (M,)
    
    # Launch the Triton kernel.
    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M, N,
        logits.stride(0),
        logits.stride(1),
    )

    return loss
"""
        return {"code": kernel_code}
