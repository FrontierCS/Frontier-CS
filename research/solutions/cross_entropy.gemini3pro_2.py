import torch

class Solution:
    def solve(self, spec_path=None):
        return {"code": r"""
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
    key=['N']
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, loss_ptr,
    stride_logits_m, stride_logits_n, stride_targets_m,
    N,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Calculate pointers for the current row
    row_logits_ptr = logits_ptr + pid * stride_logits_m
    target_idx_ptr = targets_ptr + pid * stride_targets_m
    
    # Load the target class index for this sample
    target_idx = tl.load(target_idx_ptr)
    
    # Load the specific logit value corresponding to the target class
    # We do this first or separate from the loop to ensure we have it
    # Assumes target_idx is within [0, N)
    target_val_ptr = row_logits_ptr + target_idx * stride_logits_n
    target_val = tl.load(target_val_ptr).to(tl.float32)
    
    # Initialize accumulators for Online Softmax
    # m_global: running max
    # s_global: running sum of exponentials
    m_global = float("-inf")
    s_global = 0.0
    
    # Iterate over the row in blocks
    # This handles cases where N > BLOCK_SIZE or simply tiles the computation
    for off in range(0, N, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < N
        
        # Load a chunk of logits
        a_ptr = row_logits_ptr + cols * stride_logits_n
        # Load with -inf for masked values to allow correct max/sum computation
        val = tl.load(a_ptr, mask=mask, other=float("-inf")).to(tl.float32)
        
        # Compute local max for this chunk
        m_local = tl.max(val, axis=0)
        
        # Update global max using online softmax formula
        m_new = tl.maximum(m_global, m_local)
        
        # Update global sum
        # s_global = s_global * exp(m_global - m_new) + sum(exp(val - m_new))
        s_global = s_global * tl.exp(m_global - m_new) + tl.sum(tl.exp(val - m_new), axis=0)
        
        m_global = m_new
        
    # Final cross entropy loss calculation
    # loss = -log_likelihood = - (logits[target] - log(sum(exp(logits))))
    # loss = log(sum) + max_val - target_val
    loss = tl.log(s_global) + m_global - target_val
    
    # Store the result
    tl.store(loss_ptr + pid, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using Triton.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss
    """
    M, N = logits.shape
    
    # Allocate output tensor
    losses = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    # Grid configuration: one program instance per row (sample)
    grid = lambda META: (M,)
    
    # Launch kernel
    cross_entropy_kernel[grid](
        logits, targets, losses,
        logits.stride(0), logits.stride(1), targets.stride(0),
        N
    )
    
    return losses
"""}