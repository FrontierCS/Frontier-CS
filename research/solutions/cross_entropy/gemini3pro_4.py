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
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8, num_stages=3),
    ],
    key=['n_cols'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    n_cols,
    BLOCK_SIZE: tl.constexpr
):
    # Map program ID to row index
    row_idx = tl.program_id(0)
    
    # Pointers to the current row
    logits_row_start = logits_ptr + row_idx * stride_logits_m
    target_idx = tl.load(targets_ptr + row_idx * stride_targets_m)
    
    # Accumulators for Online Softmax (Welford's algorithm adaptation)
    # m_prev: Current maximum value
    # d_prev: Current sum of exponentials (scaled by m_prev)
    m_prev = -float('inf')
    d_prev = 0.0
    
    # Accumulator for the specific target logit value
    target_val = 0.0

    # Iterate over the row in blocks
    for off in range(0, n_cols, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < n_cols
        
        # Load logits chunk
        # Casting to float32 ensures higher precision for the exponential sum
        a = tl.load(logits_row_start + cols * stride_logits_n, mask=mask, other=-float('inf')).to(tl.float32)
        
        # Online Softmax Update
        m_curr = tl.max(a, 0)
        m_new = tl.max(m_curr, m_prev)
        
        # Update sum of exps: d_new = d_prev * exp(m_prev - m_new) + sum(exp(a - m_new))
        d_prev = d_prev * tl.exp(m_prev - m_new) + tl.sum(tl.exp(a - m_new), 0)
        m_prev = m_new
        
        # Extract the target logit if it exists in the current block
        # mask is implicitly handled because 'a' has -inf where invalid, 
        # and target_idx < n_cols ensures we select a valid value.
        target_val += tl.sum(tl.where(cols == target_idx, a, 0.0))

    # Final Loss Calculation
    # Loss = -log(softmax(x_target)) = -x_target + log(sum(exp(x)))
    # LogSumExp = m_prev + log(d_prev)
    lse = m_prev + tl.log(d_prev)
    loss = lse - target_val
    
    tl.store(output_ptr + row_idx, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Computes Cross Entropy Loss using Triton.
    Args:
        logits: (M, N) tensor
        targets: (M,) tensor of indices
    Returns:
        (M,) tensor of losses
    """
    M, N = logits.shape
    
    # Allocate output tensor
    losses = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    # Grid configuration: One kernel instance per row (sample)
    grid = (M,)
    
    # Launch kernel
    cross_entropy_kernel[grid](
        logits, targets, losses,
        logits.stride(0), logits.stride(1),
        targets.stride(0),
        N
    )
    
    return losses
"""
        return {"code": code}