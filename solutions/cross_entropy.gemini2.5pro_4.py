import torch

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
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M, N,
    logits_stride_m,
    logits_stride_n,
    BLOCK_SIZE_N: tl.constexpr
):
    \"\"\"
    Triton kernel for cross entropy loss.
    Each program instance computes the loss for one sample (one row of logits).
    \"\"\"
    # Get the row index for the current program instance
    pid = tl.program_id(axis=0)
    
    # Pointer to the start of the current row in the logits tensor
    row_logits_ptr = logits_ptr + pid * logits_stride_m
    
    # Offsets for the columns in the row, to be processed in blocks
    n_offsets = tl.arange(0, BLOCK_SIZE_N)
    
    # --- Pass 1: Find the maximum logit value in the row for numerical stability ---
    # Initialize the maximum value to negative infinity
    max_val = -float('inf')
    
    # Iterate over the columns of the row in blocks of BLOCK_SIZE_N
    for offset in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        # Calculate the offsets for the current block
        current_offsets = offset * BLOCK_SIZE_N + n_offsets
        # Create a mask to handle the last block if N is not a multiple of BLOCK_SIZE_N
        mask = current_offsets < N
        
        # Load the block of logits, applying the mask
        # Out-of-bounds elements are replaced with -inf to not affect the max operation
        logits_block = tl.load(row_logits_ptr + current_offsets * logits_stride_n, mask=mask, other=-float('inf'))
        
        # Find the maximum value within the loaded block
        block_max = tl.max(logits_block, axis=0)
        
        # Update the row's maximum value
        max_val = tl.maximum(max_val, block_max)

    # --- Pass 2: Compute the log-sum-exp numerator (sum of exponentials) ---
    # Initialize the numerator for the softmax calculation
    numerator = 0.0
    
    # Iterate over the columns of the row again
    for offset in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        # Calculate offsets and mask for the current block, same as in Pass 1
        current_offsets = offset * BLOCK_SIZE_N + n_offsets
        mask = current_offsets < N
        
        # Load the block of logits
        logits_block = tl.load(row_logits_ptr + current_offsets * logits_stride_n, mask=mask, other=0.0)
        
        # Subtract the maximum logit value for numerical stability
        logits_block = logits_block - max_val
        
        # Compute the exponential of the shifted logits
        exp_logits = tl.exp(logits_block)
        
        # Apply the mask to zero out contributions from out-of-bounds elements
        exp_logits = tl.where(mask, exp_logits, 0.0)
        
        # Accumulate the sum of the exponentials
        numerator += tl.sum(exp_logits, axis=0)
        
    # Compute the log-sum-exp value, which is the denominator of the log-softmax
    lse = max_val + tl.log(numerator)
    
    # --- Final loss calculation ---
    # Load the target class index for the current row
    target_idx_ptr = targets_ptr + pid
    target_idx = tl.load(target_idx_ptr)
    
    # Load the logit corresponding to the target class
    target_logit_ptr = row_logits_ptr + target_idx * logits_stride_n
    target_logit = tl.load(target_logit_ptr)
    
    # Calculate the cross-entropy loss: -log(p_target) = log(sum(exp(logits))) - logit_target
    loss = lse - target_logit
    
    # Store the computed loss for the current row into the output tensor
    loss_ptr_out = loss_ptr + pid
    tl.store(loss_ptr_out, loss)


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
    
    # Create the output tensor for the loss values
    loss = torch.empty((M,), device=logits.device, dtype=torch.float32)
    
    # The grid for the kernel launch will have M programs, one for each sample.
    grid = (M,)
    
    # Launch the Triton kernel
    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M, N,
        logits.stride(0),
        logits.stride(1),
        # BLOCK_SIZE_N is automatically selected by the autotuner
    )
    
    return loss
"""
        return {"code": kernel_code}
