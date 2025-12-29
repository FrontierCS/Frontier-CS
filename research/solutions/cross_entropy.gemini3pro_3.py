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
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8, num_stages=3),
    ],
    key=['n_cols'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_output_m,
    n_cols,
    BLOCK_SIZE: tl.constexpr
):
    # Each program instance handles one row (batch sample)
    row_idx = tl.program_id(0)
    
    # Calculate pointers to the start of the current row
    row_logits_ptr = logits_ptr + row_idx * stride_logits_m
    row_targets_ptr = targets_ptr + row_idx * stride_targets_m
    row_output_ptr = output_ptr + row_idx * stride_output_m
    
    # Load the target class index for this sample
    target_idx = tl.load(row_targets_ptr)
    
    # Initialize statistics for online softmax (stable log-sum-exp)
    # m_prev: running maximum value
    # d_prev: running denominator (sum of exponentials)
    m_prev = -float('inf')
    d_prev = 0.0
    
    # Loop over the columns in blocks
    for off in range(0, n_cols, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < n_cols
        
        # Load a block of logits
        # Use -inf for padding to ensure they don't affect max or sum
        val = tl.load(row_logits_ptr + cols * stride_logits_n, mask=mask, other=-float('inf'))
        # Ensure calculations happen in float32 for numerical stability
        val = val.to(tl.float32)
        
        # Online Softmax update
        m_curr = tl.max(val, 0)
        m_new = tl.max(m_prev, m_curr)
        
        # Update denominator: rescale previous sum and add new block sum
        alpha = tl.exp(m_prev - m_new)
        d_prev = d_prev * alpha + tl.sum(tl.exp(val - m_new), 0)
        
        m_prev = m_new

    # Load the specific logit corresponding to the target class
    # Cast to float32 to match the precision of accumulators
    target_val = tl.load(row_logits_ptr + target_idx * stride_logits_n).to(tl.float32)
    
    # Compute Negative Log Likelihood Loss
    # Loss = -log(softmax(target)) 
    #      = -log(exp(target - max) / sum(exp(x - max)))
    #      = -(target - max - log(sum_exp))
    #      = log(sum_exp) + max - target
    # Here d_prev = sum(exp(x - m_prev)), so:
    loss = tl.log(d_prev) + m_prev - target_val
    
    # Store result
    tl.store(row_output_ptr, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    
    # Ensure targets are contiguous or handle strides correctly in kernel call
    # Output tensor initialization
    losses = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    # 1D Grid: one kernel instance per batch sample
    grid = (M,)
    
    cross_entropy_kernel[grid](
        logits, 
        targets, 
        losses,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        losses.stride(0),
        N
    )
    
    return losses
"""
        }