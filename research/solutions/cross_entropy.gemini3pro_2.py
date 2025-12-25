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
        triton.Config({'BLOCK_SIZE': 1024, 'num_warps': 4}, num_stages=2),
        triton.Config({'BLOCK_SIZE': 2048, 'num_warps': 8}, num_stages=2),
        triton.Config({'BLOCK_SIZE': 4096, 'num_warps': 8}, num_stages=3),
    ],
    key=['N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, 
    stride_logits_m, 
    stride_logits_n,
    targets_ptr,
    stride_targets_m,
    loss_ptr,
    stride_loss_m,
    N,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Pointers
    logits_row_start = logits_ptr + pid * stride_logits_m
    
    # Load target index
    target_idx = tl.load(targets_ptr + pid * stride_targets_m)
    
    # Load target logit
    # Convert to float32 for numerical stability in loss calculation
    target_logit_ptr = logits_row_start + target_idx * stride_logits_n
    target_logit = tl.load(target_logit_ptr).to(tl.float32)
    
    # Online Softmax Accumulation
    # m_i: running max
    # l_i: running sum of exponentials (shifted by m_i)
    # Initialize m_i to a very small finite value (-1e30) to handle initial -inf blocks gracefully
    # and avoid NaN generation in (m_i - m_new) when both are -inf.
    m_i = -1.0e30
    l_i = 0.0
    
    for off in range(0, N, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < N
        
        # Load logits block
        vals = tl.load(logits_row_start + cols * stride_logits_n, mask=mask, other=-float('inf'))
        vals = vals.to(tl.float32)
        
        # Update statistics using online softmax logic
        m_curr = tl.max(vals, 0)
        m_new = tl.maximum(m_i, m_curr)
        
        # Update sum of exponentials
        l_i = l_i * tl.exp(m_i - m_new) + tl.sum(tl.exp(vals - m_new), 0)
        m_i = m_new
        
    # Final Loss Computation
    # loss = log(sum(exp(x_j))) - x_target
    #      = log(l_i * exp(m_i)) - x_target
    #      = log(l_i) + m_i - x_target
    loss = tl.log(l_i) + m_i - target_logit
    
    tl.store(loss_ptr + pid * stride_loss_m, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using Triton.
    
    Args:
        logits: Input tensor of shape (M, N)
        targets: Input tensor of shape (M,)
    
    Returns:
        Output tensor of shape (M,)
    """
    M, N = logits.shape
    
    # Ensure targets is on correct device and shape
    if targets.dim() != 1 or targets.shape[0] != M:
        raise ValueError("targets must be 1D tensor of shape (M,)")
        
    # Output tensor
    loss = torch.empty((M,), dtype=torch.float32, device=logits.device)
    
    # Grid: One kernel instance per sample (row)
    grid = lambda META: (M,)
    
    cross_entropy_kernel[grid](
        logits, 
        logits.stride(0), 
        logits.stride(1),
        targets,
        targets.stride(0),
        loss,
        loss.stride(0),
        N
    )
    
    return loss
"""
        }
