import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Triton kernel implementation as a Python code string.
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 512}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=16, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, loss_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_loss_m,
    BLOCK_SIZE_N: tl.constexpr,
):
    # Each program computes the loss for one row of the logits tensor.
    pid_m = tl.program_id(axis=0)

    # Pointers to the current row in logits and the corresponding target/loss.
    row_logits_ptr = logits_ptr + pid_m * stride_logits_m
    target_ptr = targets_ptr + pid_m * stride_targets_m
    loss_out_ptr = loss_ptr + pid_m * stride_loss_m

    # --- Pass 1: Find the maximum logit value for the row for numerical stability.
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    row_max = -float('inf')
    # Iterate over the row in blocks of BLOCK_SIZE_N.
    for i in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        current_offs = i * BLOCK_SIZE_N + offs_n
        mask = current_offs < N
        logits_block = tl.load(row_logits_ptr + current_offs * stride_logits_n, mask=mask, other=-float('inf'))
        # Update the running maximum.
        block_max = tl.max(logits_block, axis=0)
        row_max = tl.maximum(row_max, block_max)

    # --- Pass 2: Compute log-sum-exp: `lse = max + log(sum(exp(logits - max)))`.
    sum_exp = 0.0
    # Iterate over the row again.
    for i in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        current_offs = i * BLOCK_SIZE_N + offs_n
        mask = current_offs < N
        logits_block = tl.load(row_logits_ptr + current_offs * stride_logits_n, mask=mask, other=-float('inf'))
        # Subtract the max, exponentiate, and sum. exp(-inf) is 0.
        exp_logits = tl.exp(logits_block - row_max)
        sum_exp += tl.sum(exp_logits, axis=0)
    
    lse = row_max + tl.log(sum_exp)

    # --- Final Loss Calculation: Loss = lse - logit_of_correct_class.
    target_idx = tl.load(target_ptr)
    target_logit = tl.load(row_logits_ptr + target_idx * stride_logits_n)
    loss = lse - target_logit
    
    # Store the result.
    tl.store(loss_out_ptr, loss)


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
    
    # Create the output tensor.
    loss = torch.empty((M,), dtype=torch.float32, device=logits.device)

    # The grid is defined so that each program computes one row.
    grid = (M,)

    # Launch the kernel.
    _cross_entropy_kernel[grid](
        logits, targets, loss,
        M, N,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        loss.stride(0),
    )
    return loss
"""
        return {"code": kernel_code}
