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
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
    ],
    key=['N']
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, out_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    N,
    BLOCK_SIZE: tl.constexpr
):
    # Map the program instance to the row of the input
    pid = tl.program_id(0)
    
    # Calculate pointers to the start of the row
    row_logits_ptr = logits_ptr + pid * stride_logits_m
    
    # Load the target class index for this sample
    target_idx = tl.load(targets_ptr + pid * stride_targets_m)
    
    # Load the logit corresponding to the target class
    # We do this separately because it's a scalar load and critical for the final subtraction
    target_val = tl.load(row_logits_ptr + target_idx * stride_logits_n)
    
    # Online Softmax / LogSumExp computation
    # We iterate over the row in blocks to compute max and sum-exp safely
    
    m_i = -float('inf')  # Running max
    s_i = 0.0            # Running sum of exponentials (shifted by m_i)
    
    for off in range(0, N, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < N
        
        # Load a block of logits
        val = tl.load(row_logits_ptr + cols * stride_logits_n, mask=mask, other=-float('inf'))
        
        # Compute local max in this block
        block_max = tl.max(val, 0)
        
        # Update global max
        new_m_i = tl.maximum(m_i, block_max)
        
        # Update running sum:
        # s_new = s_old * exp(m_old - m_new) + sum(exp(val - m_new))
        s_i = s_i * tl.exp(m_i - new_m_i) + tl.sum(tl.exp(val - new_m_i), 0)
        
        m_i = new_m_i
        
    # Final cross entropy loss = log(sum(exp(x_j))) - x_target
    # log_sum_exp = m_i + log(s_i)
    loss = m_i + tl.log(s_i) - target_val
    
    # Store the result
    tl.store(out_ptr + pid, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Cross entropy loss computation using Triton.
    
    Args:
        logits: Input tensor of shape (M, N)
        targets: Input tensor of shape (M,)
    
    Returns:
        Output tensor of shape (M,)
    \"\"\"
    # Ensure inputs are on CUDA
    if logits.device.type != 'cuda':
        logits = logits.cuda()
    if targets.device.type != 'cuda':
        targets = targets.cuda()

    M, N = logits.shape
    
    # Allocate output
    out = torch.empty(M, dtype=torch.float32, device=logits.device)
    
    # Grid: One kernel instance per row (sample)
    grid = (M,)
    
    _cross_entropy_kernel[grid](
        logits, targets, out,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        N
    )
    
    return out
"""
        }