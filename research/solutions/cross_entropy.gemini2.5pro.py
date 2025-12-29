class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 512}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=16, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, loss_ptr,
    N,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_loss_m,
    BLOCK_SIZE_N: tl.constexpr,
):
    # Each program instance computes the loss for a single sample (row).
    m_idx = tl.program_id(0)

    # Pointers for the current row.
    logits_row_ptr = logits_ptr + m_idx * stride_logits_m
    target_ptr = targets_ptr + m_idx * stride_targets_m
    loss_out_ptr = loss_ptr + m_idx * stride_loss_m

    # Use the online softmax algorithm for numerical stability.
    # This involves a single pass over the row to compute the log-sum-exp.
    # Initialize max accumulator to -infinity and sum accumulator to 0.
    m = -float('inf')
    s = 0.0

    # Iterate over the N dimension in blocks.
    offsets_n = tl.arange(0, BLOCK_SIZE_N)
    for off in range(0, N, BLOCK_SIZE_N):
        current_offsets = off + offsets_n
        mask = current_offsets < N
        
        # Load a block of logits, handling non-contiguous memory via strides.
        # Mask out-of-bounds elements with -infinity.
        x = tl.load(logits_row_ptr + current_offsets * stride_logits_n, mask=mask, other=-float('inf'))

        # Update the max and sum accumulators.
        m_new = tl.maximum(m, tl.max(x, axis=0))
        
        # Rescale the sum 's' with the new max to prevent overflow.
        s = s * tl.exp(m - m_new)
        p = tl.exp(x - m_new)
        s = s + tl.sum(p, axis=0)
        
        m = m_new

    # Final log-sum-exp value.
    log_sum_exp = m + tl.log(s)

    # Load the target index and the corresponding ground-truth logit.
    target_idx = tl.load(target_ptr)
    target_logit = tl.load(logits_row_ptr + target_idx * stride_logits_n)

    # Compute the final loss.
    loss = log_sum_exp - target_logit

    # Handle the edge case where all logits are -inf.
    # In this case, log_sum_exp = -inf and target_logit = -inf, leading to NaN.
    # The correct loss should be +inf, matching PyTorch's behavior.
    all_logits_neg_inf = (m == -float('inf'))
    loss = tl.where(all_logits_neg_inf, float('inf'), loss)

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
    
    # Allocate the output tensor.
    loss = torch.empty((M,), device=logits.device, dtype=torch.float32)

    # Launch one program per row of the logits tensor.
    grid = (M, )
    
    # Call the Triton kernel.
    _cross_entropy_kernel[grid](
        logits, targets, loss,
        N,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        loss.stride(0),
    )

    return loss
"""
        return {"code": kernel_code}