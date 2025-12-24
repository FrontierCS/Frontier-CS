import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_N': 2048}, num_warps=4),
        triton.Config({'BLOCK_N': 2048}, num_warps=8),
        triton.Config({'BLOCK_N': 4096}, num_warps=8),
        triton.Config({'BLOCK_N': 8192}, num_warps=8),
        triton.Config({'BLOCK_N': 8192}, num_warps=16),
    ],
    key=['n_cols'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, 
    targets_ptr, 
    loss_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets,
    n_cols,
    BLOCK_N: tl.constexpr
):
    # Map program ID to row index
    row_idx = tl.program_id(0)
    
    # Calculate pointers for the current row
    logits_row_ptr = logits_ptr + row_idx * stride_logits_m
    loss_row_ptr = loss_ptr + row_idx
    target_ptr = targets_ptr + row_idx * stride_targets
    
    # Load target class index
    target_idx = tl.load(target_ptr)
    
    # Load the logit value corresponding to the target class
    # We do this separately to avoid branching or masking inside the reduction loop
    target_logit_ptr = logits_row_ptr + target_idx * stride_logits_n
    target_logit = tl.load(target_logit_ptr)
    
    # Initialize online softmax accumulators
    # m_i: Running maximum of logits seen so far
    # l_i: Running sum of exponentials exp(x - m_i)
    m_i = -float('inf')
    l_i = 0.0
    
    # Iterate over columns in blocks
    for off_n in range(0, n_cols, BLOCK_N):
        cols = off_n + tl.arange(0, BLOCK_N)
        mask = cols < n_cols
        
        # Load block of logits, pad with -inf for safety
        a = tl.load(logits_row_ptr + cols * stride_logits_n, mask=mask, other=-float('inf'))
        # Cast to float32 for numerical stability
        a = a.to(tl.float32)
        
        # Compute max of current block
        m_curr = tl.max(a, 0)
        
        # Update running max
        m_new = tl.maximum(m_i, m_curr)
        
        # Compute scaling factor: exp(m_i - m_new)
        # We need to handle the initialization case where m_i is -inf
        # If m_i is -inf, we assume the previous sum l_i (0.0) should be scaled by 0.0
        # regardless of m_new (to avoid NaN if m_new is also -inf)
        raw_diff = m_i - m_new
        scale = tl.exp(raw_diff)
        scale = tl.where(m_i == -float('inf'), 0.0, scale)
        
        # Update running sum: l_i * scale + sum(exp(a - m_new))
        l_i = l_i * scale + tl.sum(tl.exp(a - m_new))
        
        # Update m_i
        m_i = m_new

    # Compute final loss
    # Loss = log(sum(exp(x_j))) - x_target
    #      = m_i + log(l_i) - target_logit
    target_logit = target_logit.to(tl.float32)
    loss = m_i + tl.log(l_i) - target_logit
    
    # Store result
    tl.store(loss_row_ptr, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    
    # Allocate output tensor
    losses = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    # Grid definition: One kernel instance per row
    grid = (M,)
    
    # Launch kernel
    # Pass strides explicitly to handle memory layout
    cross_entropy_kernel[grid](
        logits, 
        targets, 
        losses,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        N
    )
    
    return losses
"""
        return {"code": code}
