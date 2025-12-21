class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 256}, num_warps=2),
        triton.Config({'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4),
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
    M: tl.int32,
    N: tl.int32,
    logits_row_stride: tl.int32,
    BLOCK_SIZE_N: tl.constexpr,
):
    \"\"\"
    Triton kernel for cross entropy loss.
    Each program instance computes the loss for a single row of the logits tensor.
    The computation is done in two passes over each row to ensure numerical stability.
    Pass 1: Find the maximum logit value for the row.
    Pass 2: Compute the log-sum-exp using the max value for stability.
    \"\"\"
    # Get the row index (batch index) for this program instance.
    pid = tl.program_id(axis=0)

    # Pointer to the start of the current row in the logits tensor.
    row_logits_ptr = logits_ptr + pid * logits_row_stride
    
    # --- Pass 1: Find max logit and load the target logit ---

    # Load the target class index for the current row.
    target_idx = tl.load(targets_ptr + pid)
    
    # Load the logit value corresponding to the target class. This is a scalar load.
    # The value is converted to float32 for high-precision computation.
    logit_target = tl.load(row_logits_ptr + target_idx).to(tl.float32)

    # Initialize the maximum value for the row to negative infinity.
    row_max = -float('inf')
    # Create a range of offsets for a block of the row.
    offsets_n = tl.arange(0, BLOCK_SIZE_N)
    
    # Iterate over the row in blocks to find the maximum logit value.
    for i in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        # Calculate offsets for the current block.
        current_offsets = offsets_n + i * BLOCK_SIZE_N
        # Create a mask to handle rows where N is not a multiple of BLOCK_SIZE_N.
        mask = current_offsets < N
        
        # Load a block of logits, using -inf for out-of-bounds elements
        # so they don't affect the maximum operation.
        block_logits = tl.load(row_logits_ptr + current_offsets, mask=mask, other=-float('inf'))
        
        # Update the running maximum for the row.
        current_max = tl.max(block_logits, axis=0)
        row_max = tl.maximum(row_max, current_max)
    
    # --- Pass 2: Compute sum of exponentials ---

    # Initialize the sum of exponentials to zero.
    sum_exp = 0.0
    # Iterate over the row again.
    for i in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        current_offsets = offsets_n + i * BLOCK_SIZE_N
        mask = current_offsets < N
        
        # Load the block of logits again.
        block_logits = tl.load(row_logits_ptr + current_offsets, mask=mask, other=-float('inf'))
        
        # Subtract the max value for numerical stability (log-sum-exp trick).
        # Convert to float32 before exponentiation.
        stable_logits = block_logits.to(tl.float32) - row_max
        exp_logits = tl.exp(stable_logits)
        
        # Accumulate the sum of exponentials.
        sum_exp += tl.sum(exp_logits, axis=0)

    # --- Final loss calculation ---
    # loss = log(sum(exp(x))) - x_target
    # where log(sum(exp(x))) = max(x) + log(sum(exp(x - max(x))))
    log_sum_exp = row_max + tl.log(sum_exp)
    loss = log_sum_exp - logit_target
    
    # Store the final loss value for the current row.
    tl.store(output_ptr + pid, loss)


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
    
    # Allocate the output tensor for the loss. Loss is always float32.
    loss = torch.empty((M,), dtype=torch.float32, device=logits.device)
    
    # The grid is 1D with M programs, one for each row in the batch.
    grid = (M,)
    
    # Launch the Triton kernel.
    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M,
        N,
        logits.stride(0),
        # BLOCK_SIZE_N is determined by the autotuner.
    )
    
    return loss
"""
        return {"code": kernel_code}
