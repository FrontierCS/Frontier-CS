import torch

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
        triton.Config({'BLOCK_SIZE': 1024, 'num_stages': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048, 'num_stages': 4}, num_warps=8),
    ],
    key=['n_cols'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    stride_logits_m, stride_logits_n,
    n_cols,
    BLOCK_SIZE: tl.constexpr
):
    # Map program ID to row index
    row_idx = tl.program_id(0)
    
    # Calculate pointer to the start of the row
    logits_row_ptr = logits_ptr + row_idx * stride_logits_m
    
    # Load target index (int64)
    target_idx = tl.load(targets_ptr + row_idx)
    
    # Load the specific target logit value
    # We do this separately to avoid checking indices inside the inner loop
    # Convert to float32 to ensure precision in the final loss subtraction
    target_val_ptr = logits_row_ptr + target_idx * stride_logits_n
    target_val = tl.load(target_val_ptr).to(tl.float32)
    
    # Online Softmax Accumulators
    # m_global: Global maximum value found so far
    # s_global: Global sum of exponentials found so far (scaled by m_global)
    m_global = float("-inf")
    s_global = 0.0
    
    # Iterate over columns in blocks
    for off in range(0, n_cols, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < n_cols
        
        # Load logits block
        a_ptr = logits_row_ptr + cols * stride_logits_n
        # Load as float32 for numerical stability during accumulation
        val = tl.load(a_ptr, mask=mask, other=float("-inf")).to(tl.float32)
        
        # Calculate max in current block
        m_curr = tl.max(val, 0)
        
        # Update global max
        m_new = tl.maximum(m_global, m_curr)
        
        # Update global sum: s_new = s_old * exp(m_old - m_new) + sum(exp(val - m_new))
        s_global = s_global * tl.exp(m_global - m_new) + tl.sum(tl.exp(val - m_new), 0)
        m_global = m_new

    # Calculate Cross Entropy Loss
    # Loss = -log(exp(x_target) / sum(exp(x))) 
    #      = log(sum(exp(x))) - x_target
    #      = log(s_global * exp(m_global)) - x_target
    #      = log(s_global) + m_global - x_target
    loss = tl.log(s_global) + m_global - target_val
    
    # Store result
    tl.store(output_ptr + row_idx, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    
    # Ensure targets are contiguous for simple indexing in kernel
    if not targets.is_contiguous():
        targets = targets.contiguous()
        
    # Allocate output tensor (float32)
    output = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    # Launch grid: one kernel per row (sample)
    grid = (M,)
    
    _cross_entropy_kernel[grid](
        logits, targets, output,
        logits.stride(0), logits.stride(1),
        N
    )
    
    return output
"""
        }