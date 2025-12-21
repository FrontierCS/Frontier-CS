import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({}, num_warps=4),
        triton.Config({}, num_warps=8),
        triton.Config({}, num_warps=16),
        triton.Config({}, num_warps=32),
    ],
    key=['N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, out_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets,
    N,
    BLOCK_SIZE: tl.constexpr
):
    # Program ID
    row_idx = tl.program_id(0)
    
    # Pointers
    logits_row_ptr = logits_ptr + row_idx * stride_logits_m
    target_ptr_row = targets_ptr + row_idx * stride_targets
    output_ptr_row = out_ptr + row_idx
    
    # Load entire row of logits
    # We use a block size that covers N (calculated in wrapper)
    cols = tl.arange(0, BLOCK_SIZE)
    mask = cols < N
    
    # Load data
    # Cast to float32 for precision in exp/sum
    # Use -inf for padding so it doesn't affect max calculation or sum_exp
    logits = tl.load(logits_row_ptr + cols * stride_logits_n, mask=mask, other=-float('inf')).to(tl.float32)
    
    # 1. Compute Max for numerical stability
    max_val = tl.max(logits, 0)
    
    # 2. Compute Sum of Exponentials
    # shifted = logits - max_val
    # padded values: -inf - max_val = -inf -> exp(-inf) = 0
    shifted_logits = logits - max_val
    sum_exp = tl.sum(tl.exp(shifted_logits), 0)
    
    # 3. Compute LogSumExp
    # log(sum(exp(x - m))) + m
    log_sum_exp = max_val + tl.log(sum_exp)
    
    # 4. Get the target class logit
    target_idx = tl.load(target_ptr_row)
    
    # Load specific logit from global memory
    # Accessing via logits_row_ptr + target_idx * stride
    target_logit = tl.load(logits_row_ptr + target_idx * stride_logits_n).to(tl.float32)
    
    # 5. Compute Loss
    # loss = -target_logit + log_sum_exp
    loss = log_sum_exp - target_logit
    
    # Store result
    tl.store(output_ptr_row, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    
    # Allocate output
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    
    # Determine Block Size
    # Use next power of 2 to handle the reduction efficiently in one block if possible
    BLOCK_SIZE = triton.next_power_of_2(N)
    
    # Launch Kernel
    grid = (M,)
    
    cross_entropy_kernel[grid](
        logits, targets, output,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        N,
        BLOCK_SIZE=BLOCK_SIZE
    )
    
    return output
"""
        }
