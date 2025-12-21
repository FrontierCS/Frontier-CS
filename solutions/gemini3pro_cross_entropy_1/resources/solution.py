import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8, num_stages=4),
    ],
    key=['n_cols']
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, loss_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    n_cols,
    BLOCK_SIZE: tl.constexpr
):
    # Program ID corresponds to the row index
    row_idx = tl.program_id(0)
    
    # Calculate pointer to the start of the row in logits
    logits_row_ptr = logits_ptr + row_idx * stride_logits_m
    
    # Load the target class index for this row
    # targets_ptr points to int64, so we load an int64 index
    target_idx = tl.load(targets_ptr + row_idx * stride_targets_m)
    
    # Load the logit value corresponding to the target class
    # We load this scalar directly to subtract later
    # Casting to float32 ensures precision matching the accumulation
    target_logit = tl.load(logits_row_ptr + target_idx * stride_logits_n).to(tl.float32)
    
    # Initialize accumulators for Online Softmax (LogSumExp)
    # m_prev: running maximum
    # d_prev: running sum of exponentials (normalized by m_prev)
    m_prev = -float('inf')
    d_prev = 0.0
    
    # Loop over the columns in blocks
    for off in range(0, n_cols, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < n_cols
        
        # Load a chunk of logits
        # We use other=-inf so padded values don't affect max calculation
        # Cast to float32 for numerical stability
        val = tl.load(logits_row_ptr + cols * stride_logits_n, mask=mask, other=-float('inf')).to(tl.float32)
        
        # Compute max of current chunk
        m_curr = tl.max(val, 0)
        
        # Update global max
        m_new = tl.maximum(m_prev, m_curr)
        
        # Update running sum of exponentials:
        # 1. Rescale previous sum: d_prev * exp(m_prev - m_new)
        # 2. Add current chunk sum: sum(exp(val - m_new))
        d_prev = d_prev * tl.exp(m_prev - m_new)
        d_curr = tl.sum(tl.exp(val - m_new), 0)
        
        d_prev = d_prev + d_curr
        m_prev = m_new
        
    # Final Loss Calculation
    # Loss_i = -x_{i, target} + log(sum(exp(x_{i, j})))
    #        = -target_logit + (m_prev + log(d_prev))
    loss = m_prev + tl.log(d_prev) - target_logit
    
    # Store result
    tl.store(loss_ptr + row_idx, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using Triton.
    
    Args:
        logits: Input tensor of shape (M, N)
        targets: Input tensor of shape (M,) - int64
    
    Returns:
        Output tensor of shape (M,) - float32
    """
    M, N = logits.shape
    
    # Output tensor must be float32
    loss = torch.empty(M, dtype=torch.float32, device=logits.device)
    
    # Grid configuration: One kernel instance per row (sample)
    grid = (M,)
    
    cross_entropy_kernel[grid](
        logits, targets, loss,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        N
    )
    
    return loss
"""
        }
