import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with a string containing the Python code for the kernel.
        """
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
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
    logits_ptr,
    targets_ptr,
    output_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_output_m,
    BLOCK_SIZE_N: tl.constexpr,
):
    # Each program instance computes the loss for one row (one sample).
    pid = tl.program_id(axis=0)

    # Pointers for the current row
    row_logits_ptr = logits_ptr + pid * stride_logits_m
    row_targets_ptr = targets_ptr + pid * stride_targets_m
    row_output_ptr = output_ptr + pid * stride_output_m

    # === Pass 1: Find the maximum logit value in the row for numerical stability ===
    # This is the core of the log-sum-exp trick.
    row_max = -float('inf')
    # Pre-calculate column offsets for the loop
    offsets_n = tl.arange(0, BLOCK_SIZE_N)
    
    # Iterate over the columns of the current row in blocks
    for col_offset in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        cols = col_offset * BLOCK_SIZE_N + offsets_n
        mask = cols < N
        
        # Load a block of logits safely.
        # Use -inf for out-of-bounds elements, which won't affect the max operation.
        logit_block = tl.load(row_logits_ptr + cols * stride_logits_n, mask=mask, other=-float('inf'))
        
        # Update the running maximum for the row
        current_max = tl.max(logit_block, axis=0)
        row_max = tl.maximum(row_max, current_max)

    # === Pass 2: Compute the log-sum-exp ===
    # log(sum(exp(x_i))) = m + log(sum(exp(x_i - m))) where m = max(x_i)
    
    # Initialize accumulator for the sum of exponentials
    sum_exp = 0.0
    
    # Iterate over the columns again
    for col_offset in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        cols = col_offset * BLOCK_SIZE_N + offsets_n
        mask = cols < N
        
        # Load logits, subtract the max, and exponentiate
        logit_block = tl.load(row_logits_ptr + cols * stride_logits_n, mask=mask, other=-float('inf'))
        # It's important to cast to float32 for exp and log for better precision
        shifted_logits = (logit_block - row_max).to(tl.float32)
        exp_values = tl.exp(shifted_logits)
        
        # Add to the sum, masking out-of-bounds values
        sum_exp += tl.sum(tl.where(mask, exp_values, 0.0), axis=0)
    
    # Final log-sum-exp value
    log_sum_exp = row_max + tl.log(sum_exp)

    # === Pass 3: Compute the final loss ===
    # loss = -log(softmax(x)_j) = - (x_j - log(sum(exp(x_i)))) = log(sum(exp(x_i))) - x_j
    
    # Load the target class index
    target_idx = tl.load(row_targets_ptr)
    
    # Load the logit corresponding to the target class
    target_logit = tl.load(row_logits_ptr + target_idx * stride_logits_n)

    # Calculate the cross-entropy loss
    loss = log_sum_exp - target_logit.to(tl.float32)

    # Store the result
    tl.store(row_output_ptr, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss for each sample
    """
    M, N = logits.shape
    
    # Create output tensor. The problem requires float32 output.
    loss = torch.empty(M, device=logits.device, dtype=torch.float32)

    # Grid for kernel launch. One program per row.
    grid = lambda meta: (M,)
    
    # Launch the kernel. The autotuner will pick the best BLOCK_SIZE_N.
    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M, N,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        loss.stride(0),
    )
    
    return loss
"""
        return {"code": code}