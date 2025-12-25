import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        cross_entropy_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # A range of configurations to find the optimal one for the specific hardware and problem size.
        # These configs vary block size, number of warps, and software pipelining stages.
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=16, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=32, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_fwd_kernel(
    logits_ptr, targets_ptr, loss_ptr,
    M, N,
    logits_stride_m, logits_stride_n,
    BLOCK_SIZE_N: tl.constexpr,
):
    # Each program instance computes the cross-entropy loss for a single row.
    pid_m = tl.program_id(axis=0)

    # Pointer to the start of the current row in the logits tensor.
    row_start_ptr = logits_ptr + pid_m * logits_stride_m

    # Numerically stable one-pass algorithm for log-sum-exp.
    # We maintain a running maximum `m` and a running sum of scaled exponentials `s`.
    m = -float('inf')
    s = 0.0

    # Iterate over the N columns of the row in blocks.
    for off in range(0, N, BLOCK_SIZE_N):
        # Generate column indices for the current block.
        cols = off + tl.arange(0, BLOCK_SIZE_N)
        # Create a mask to guard against out-of-bounds memory accesses.
        mask = cols < N
        
        # Load a block of logits, applying the mask.
        # Computation is done in float32 for precision.
        x = tl.load(row_start_ptr + cols * logits_stride_n, mask=mask, other=-float('inf')).to(tl.float32)

        # Update the running maximum over the row.
        m_new = tl.maximum(m, tl.max(x, axis=0))
        
        # Rescale the current sum `s` based on the new maximum and add the new values.
        # This prevents overflow/underflow during exponentiation.
        alpha = tl.exp(m - m_new)
        s = s * alpha + tl.sum(tl.exp(x - m_new), axis=0)

        # Update the maximum for the next block.
        m = m_new

    # Final log-sum-exp value.
    log_sum_exp = m + tl.log(s)

    # Load the target class index for the current row.
    target_idx = tl.load(targets_ptr + pid_m)
    
    # Load the logit value for the target class.
    target_logit = tl.load(row_start_ptr + target_idx * logits_stride_n).to(tl.float32)

    # Compute the cross-entropy loss: log(sum(exp(logits))) - logit_at_target.
    loss = log_sum_exp - target_logit

    # Store the result.
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
    
    # Create an empty tensor to store the output loss.
    loss = torch.empty((M,), dtype=torch.float32, device=logits.device)
    
    # The grid for the kernel is one-dimensional, with one program per row of the logits.
    grid = (M,)
    
    # Launch the Triton kernel.
    _cross_entropy_fwd_kernel[grid](
        logits,
        targets,
        loss,
        M, N,
        logits.stride(0),
        logits.stride(1),
    )
    
    return loss
"""
        return {"code": cross_entropy_code}
