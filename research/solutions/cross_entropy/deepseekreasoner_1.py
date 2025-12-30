import torch
import triton
import triton.language as tl
import json
import os

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 512}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 1024}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Create offsets for this block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Create masks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Load logits for this block
    logits_ptrs = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
    logits_block = tl.load(logits_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
    
    # Find max per row for numerical stability
    row_max = tl.max(logits_block, axis=1)
    
    # Compute exp(logits - max) for log-sum-exp
    logits_shifted = logits_block - row_max[:, None]
    exp_logits = tl.exp(logits_shifted)
    
    # Sum exp for log-sum-exp
    row_sum_exp = tl.sum(exp_logits, axis=1)
    
    # Compute log-softmax: logits - max - log(sum(exp(logits - max)))
    log_softmax = logits_shifted - tl.log(row_sum_exp[:, None])
    
    # Load targets for this block of rows
    targets_ptrs = targets_ptr + offs_m
    targets_block = tl.load(targets_ptrs, mask=mask_m, other=0)
    
    # Convert targets to column indices
    targets_col = targets_block[:, None] - offs_n[None, :]
    target_mask = tl.where(targets_col == 0, 1, 0).to(tl.int1)
    
    # Extract log-softmax values at target positions
    log_softmax_at_target = tl.sum(log_softmax * target_mask, axis=1)
    
    # Compute negative log-likelihood
    loss = -log_softmax_at_target
    
    # Store loss if this program handles the final column reduction
    if pid_n == 0:
        loss_ptrs = loss_ptr + offs_m
        tl.store(loss_ptrs, loss, mask=mask_m)

@triton.jit
def _cross_entropy_forward_kernel_fused(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    
    # Each program processes BLOCK_M rows
    row_start = pid * BLOCK_M
    offs_m = row_start + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Load targets for these rows
    targets_ptrs = targets_ptr + offs_m
    targets = tl.load(targets_ptrs, mask=mask_m, other=0)
    
    # Initialize reduction accumulators
    row_max = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    row_sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process columns in tiles
    for col_start in range(0, N, BLOCK_N):
        offs_n = col_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Load logits for this tile
        logits_ptrs = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
        logits_tile = tl.load(logits_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
        
        # Update row max
        tile_max = tl.max(logits_tile, axis=1)
        row_max = tl.maximum(row_max, tile_max)
        
        # Check for target columns in this tile
        targets_col = targets[:, None] - offs_n[None, :]
        target_mask = tl.where(targets_col == 0, 1, 0).to(tl.int1)
        target_logit_tile = tl.sum(logits_tile * target_mask, axis=1)
        target_logit += target_logit_tile
        
        # Need to wait for row_max update before computing exp
        # We'll compute exp in the next loop iteration or at the end
        
        # Update row_sum_exp with the old max
        # For numerical stability, we adjust by the difference between old and new max
        if col_start > 0:
            # Adjust previous sum_exp by exp(row_max_old - row_max_new)
            # We'll handle this by recomputing the entire sum after we have the final max
            pass
    
    # Now we have the final row_max, recompute sum_exp and target_logit properly
    # Reset accumulators
    row_sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    for col_start in range(0, N, BLOCK_N):
        offs_n = col_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        logits_ptrs = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
        logits_tile = tl.load(logits_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
        
        # Shift logits by row_max for numerical stability
        logits_shifted = logits_tile - row_max[:, None]
        exp_logits = tl.exp(logits_shifted)
        row_sum_exp += tl.sum(exp_logits, axis=1)
        
        # Extract target logits
        targets_col = targets[:, None] - offs_n[None, :]
        target_mask = tl.where(targets_col == 0, 1, 0).to(tl.int1)
        target_logit_tile = tl.sum(logits_tile * target_mask, axis=1)
        target_logit += target_logit_tile
    
    # Compute log-sum-exp: log(sum(exp(logits - max))) + max
    log_sum_exp = tl.log(row_sum_exp) + row_max
    
    # Compute loss: -target_logit + log_sum_exp
    loss = -target_logit + log_sum_exp
    
    # Store results
    loss_ptrs = loss_ptr + offs_m
    tl.store(loss_ptrs, loss, mask=mask_m)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 512}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 1024}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_kernel_optimized(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    
    # Each program processes BLOCK_M rows
    row_start = pid * BLOCK_M
    offs_m = row_start + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Load targets for these rows
    targets_ptrs = targets_ptr + offs_m
    targets = tl.load(targets_ptrs, mask=mask_m, other=0)
    
    # Initialize accumulators
    row_max = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    row_sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # First pass: find row max and accumulate target logits
    target_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    for col_start in range(0, N, BLOCK_N):
        offs_n = col_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Load logits for this tile
        logits_ptrs = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
        logits_tile = tl.load(logits_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
        
        # Update row max
        tile_max = tl.max(logits_tile, axis=1)
        row_max = tl.maximum(row_max, tile_max)
        
        # Check for target columns in this tile
        targets_col = targets[:, None] - offs_n[None, :]
        target_mask = tl.where(targets_col == 0, 1, 0).to(tl.int1)
        target_logit += tl.sum(logits_tile * target_mask, axis=1)
    
    # Second pass: compute log-sum-exp with proper numerical stability
    # Reset row_sum_exp
    row_sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    for col_start in range(0, N, BLOCK_N):
        offs_n = col_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        logits_ptrs = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
        logits_tile = tl.load(logits_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
        
        # Shift by row_max and compute exp
        logits_shifted = logits_tile - row_max[:, None]
        exp_logits = tl.exp(logits_shifted)
        row_sum_exp += tl.sum(exp_logits, axis=1)
    
    # Compute final loss
    log_sum_exp = tl.log(row_sum_exp) + row_max
    loss = -target_logit + log_sum_exp
    
    # Store results
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
    M, N = logits.shape
    
    # Ensure tensors are on the same device and have correct types
    assert logits.device == targets.device, "logits and targets must be on the same device"
    assert targets.dtype == torch.int64, "targets must be int64"
    
    # Allocate output tensor
    loss = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    # Choose kernel based on problem size
    if M <= 256 or N <= 1024:
        # For smaller problems, use the optimized kernel
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']),)
        _cross_entropy_forward_kernel_optimized[grid](
            logits,
            targets,
            loss,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
        )
    else:
        # For larger problems, use the two-pass kernel
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']),)
        _cross_entropy_forward_kernel_optimized[grid](
            logits,
            targets,
            loss,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
        )
    
    return loss

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # If spec_path is provided, read metadata for tuning
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                # Could use spec for further optimization
            except:
                pass
        
        # Return the code directly
        import inspect
        code = inspect.getsource(cross_entropy)
        
        # Get all related functions
        full_code = ""
        for name, obj in globals().items():
            if hasattr(obj, '__code__'):
                try:
                    if 'cross_entropy' in name or 'Solution' in name:
                        full_code += inspect.getsource(obj) + "\n\n"
                except:
                    pass
        
        return {"code": full_code}