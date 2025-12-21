import torch
import triton
import triton.language as tl
from typing import Dict, Any

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 1024, 'BLOCK_N': 16}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 512}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 64}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    
    # Create offsets for the current block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    
    # Mask for rows within bounds
    mask_m = offs_m < M
    
    # Load targets for current block
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    
    # Initialize max and sum for log-sum-exp
    row_max = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    row_sum = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Track target logits
    target_logits = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process N dimension in blocks
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        # Create column offsets
        n_offsets = start_n * BLOCK_N + offs_n
        mask_n = n_offsets < N
        
        # Load logits block
        logits_ptrs = (
            logits_ptr + 
            offs_m[:, None] * stride_logits_m + 
            n_offsets[None, :] * stride_logits_n
        )
        logits_block = tl.load(
            logits_ptrs, 
            mask=mask_m[:, None] & mask_n[None, :], 
            other=float('-inf')
        )
        
        # Check if target is in current block
        target_in_block = (targets[:, None] == n_offsets[None, :])
        target_mask = target_in_block & mask_m[:, None] & mask_n[None, :]
        target_vals = tl.where(target_mask, logits_block, 0.0)
        target_logits += tl.sum(target_vals, axis=1)
        
        # Update row max
        block_max = tl.max(logits_block, axis=1)
        row_max = tl.maximum(row_max, block_max)
        
        # Update row sum for log-sum-exp (deferred until we have final max)
        # We'll accumulate in a second pass
    
    # Second pass: compute exp sum with stable computation
    row_sum = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        n_offsets = start_n * BLOCK_N + offs_n
        mask_n = n_offsets < N
        
        logits_ptrs = (
            logits_ptr + 
            offs_m[:, None] * stride_logits_m + 
            n_offsets[None, :] * stride_logits_n
        )
        logits_block = tl.load(
            logits_ptrs, 
            mask=mask_m[:, None] & mask_n[None, :], 
            other=float('-inf')
        )
        
        # Stable computation: exp(logits - max)
        logits_stable = logits_block - row_max[:, None]
        exp_vals = tl.exp(logits_stable)
        row_sum += tl.sum(exp_vals, axis=1)
    
    # Compute final loss: -target_logit + log(sum(exp(logits)))
    log_sum_exp = tl.log(row_sum) + row_max
    loss = -target_logits + log_sum_exp
    
    # Store results
    loss_ptrs = loss_ptr + offs_m
    tl.store(loss_ptrs, loss, mask=mask_m)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 512}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 1024}, num_stages=3, num_warps=8),
    ],
    key=['M'],
)
@triton.jit
def _cross_entropy_forward_small_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    BLOCK_M: tl.constexpr
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Load targets
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    
    # Initialize accumulators
    row_max = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    row_sum = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logits = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process entire row for each sample
    for n in range(N):
        # Load single logit value
        logits_ptrs = logits_ptr + offs_m * stride_logits_m + n * stride_logits_n
        logit_val = tl.load(logits_ptrs, mask=mask_m, other=float('-inf'))
        
        # Check if this is the target
        is_target = (targets == n)
        target_logits += tl.where(is_target & mask_m, logit_val, 0.0)
        
        # Update max
        row_max = tl.maximum(row_max, logit_val)
        
        # Store for later sum (we'll accumulate in second pass)
        # We'll use local memory to store values
        # Since we can't store all values, we'll process in two passes
    
    # Second pass: compute sum of exp(logits - max)
    for n in range(N):
        logits_ptrs = logits_ptr + offs_m * stride_logits_m + n * stride_logits_n
        logit_val = tl.load(logits_ptrs, mask=mask_m, other=float('-inf'))
        
        # Stable computation
        exp_val = tl.exp(logit_val - row_max)
        row_sum += tl.where(mask_m, exp_val, 0.0)
    
    # Compute final loss
    log_sum_exp = tl.log(row_sum) + row_max
    loss = -target_logits + log_sum_exp
    
    # Store
    loss_ptrs = loss_ptr + offs_m
    tl.store(loss_ptrs, loss, mask=mask_m)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss for each sample
    """
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    assert logits.size(0) == targets.size(0), "Batch size mismatch"
    
    M, N = logits.shape
    device = logits.device
    
    # Allocate output
    loss = torch.empty(M, device=device, dtype=logits.dtype)
    
    # Choose kernel based on problem size
    if N <= 512:
        # Use simpler kernel for smaller vocabulary sizes
        grid = (triton.cdiv(M, 128),)
        _cross_entropy_forward_small_kernel[grid](
            logits, targets, loss,
            M, N,
            logits.stride(0), logits.stride(1),
            BLOCK_M=128
        )
    else:
        # Use tiled kernel for larger vocabulary sizes
        grid = (triton.cdiv(M, 128),)
        _cross_entropy_forward_kernel[grid](
            logits, targets, loss,
            M, N,
            logits.stride(0), logits.stride(1),
            BLOCK_M=128, BLOCK_N=128
        )
    
    return loss

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """Return the solution implementation."""
        # Return the code as a string
        import inspect
        current_module = __name__
        
        # Get all functions and classes defined in this module
        module_code = inspect.getsource(__import__(current_module))
        
        # Extract only the code from this file (excluding imports from other modules)
        lines = module_code.split('\n')
        filtered_lines = []
        skip_next = False
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # Skip imports, they will be added automatically
                continue
            filtered_lines.append(line)
        
        final_code = '\n'.join(filtered_lines)
        return {"code": final_code}
