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
        triton.Config({'BLOCK_SIZE_N': 256, 'ROWS_PER_PROGRAM': 1}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 512, 'ROWS_PER_PROGRAM': 1}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 1024, 'ROWS_PER_PROGRAM': 1}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 2048, 'ROWS_PER_PROGRAM': 1}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 512, 'ROWS_PER_PROGRAM': 2}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 1024, 'ROWS_PER_PROGRAM': 2}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 512, 'ROWS_PER_PROGRAM': 4}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 1024, 'ROWS_PER_PROGRAM': 4}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 4096, 'ROWS_PER_PROGRAM': 1}, num_warps=16, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 8192, 'ROWS_PER_PROGRAM': 1}, num_warps=16, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    # Tunable parameters determined by autotuner
    ROWS_PER_PROGRAM: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
):
    \"\"\"
    Triton kernel for cross entropy loss.
    Each program instance can handle multiple rows (ROWS_PER_PROGRAM) to improve occupancy.
    The computation uses a numerically stable two-pass approach for the log-sum-exp.
    \"\"\"
    pid = tl.program_id(axis=0)

    # Loop over rows assigned to this program instance
    for i in range(ROWS_PER_PROGRAM):
        pid_m = pid * ROWS_PER_PROGRAM + i
        # Boundary check to avoid processing out-of-bounds rows
        if pid_m >= M:
            return

        # Pointer to the start of the current row in the logits tensor
        row_logits_ptr = logits_ptr + pid_m * stride_logits_m

        # === Pass 1: Find the maximum logit value for the row for numerical stability ===
        offs_n_init = tl.arange(0, BLOCK_SIZE_N)
        row_max = -float('inf')
        
        for j in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
            offs_n = j * BLOCK_SIZE_N + offs_n_init
            mask = offs_n < N
            # Load a block of logits, masking out-of-bounds elements
            logits_block = tl.load(row_logits_ptr + offs_n * stride_logits_n, mask=mask, other=-float('inf'))
            # Reduce the block to find its maximum value and update the row's maximum
            current_max = tl.max(logits_block, 0)
            row_max = tl.maximum(row_max, current_max)
        
        # === Pass 2: Compute the sum of exponentiated logits (for log-sum-exp) ===
        # The numerically stable formula is: log(sum(exp(logits - max))) + max
        sum_exp = 0.0
        
        for j in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
            offs_n = j * BLOCK_SIZE_N + offs_n_init
            mask = offs_n < N
            logits_block = tl.load(row_logits_ptr + offs_n * stride_logits_n, mask=mask, other=-float('inf'))
            # Subtract the max, exponentiate, and add to the sum accumulator
            sum_exp += tl.sum(tl.exp(logits_block - row_max), 0)
        
        log_sum_exp = row_max + tl.log(sum_exp)

        # === Pass 3: Get the target logit and compute the final loss ===
        # Load the target class index for the current row
        target_idx = tl.load(targets_ptr + pid_m)
        # Load the logit corresponding to the target class
        logit_target = tl.load(row_logits_ptr + target_idx * stride_logits_n)
        
        # The cross-entropy loss is log_sum_exp - logit_target
        loss = log_sum_exp - logit_target
        
        # Store the computed loss for the current row
        tl.store(loss_ptr + pid_m, loss)

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
    
    # Input validation for robustness
    assert logits.is_cuda and targets.is_cuda, "Input tensors must be on a CUDA device."
    assert logits.dim() == 2, "Logits must be a 2D tensor."
    assert targets.dim() == 1, "Targets must be a 1D tensor."
    assert M == targets.shape[0], "Batch dimensions of logits and targets must match."
    assert targets.dtype == torch.int64, "Targets tensor must be of type int64."
    
    # Create the output tensor for the losses
    loss = torch.empty((M,), device=logits.device, dtype=torch.float32)
    
    # The grid size is dependent on the number of rows processed by each program.
    # This is determined by the autotuner. We use a lambda to make the grid
    # size dependent on the 'ROWS_PER_PROGRAM' meta-parameter.
    grid = lambda meta: (triton.cdiv(M, meta['ROWS_PER_PROGRAM']),)
    
    # Launch the Triton kernel
    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M, N,
        logits.stride(0), logits.stride(1),
    )
    
    return loss
"""
        return {"code": kernel_code}