import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 128, 'NUM_ROWS_PER_PROGRAM': 2}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256, 'NUM_ROWS_PER_PROGRAM': 2}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'NUM_ROWS_PER_PROGRAM': 2}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 128, 'NUM_ROWS_PER_PROGRAM': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256, 'NUM_ROWS_PER_PROGRAM': 4}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    logits_row_stride,
    logits_col_stride,
    BLOCK_SIZE: tl.constexpr,
    NUM_ROWS_PER_PROGRAM: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_programs = tl.num_programs(axis=0)
    
    row_start = pid * NUM_ROWS_PER_PROGRAM
    row_end = min(row_start + NUM_ROWS_PER_PROGRAM, M)
    
    for row_idx in range(row_start, row_end):
        target = tl.load(targets_ptr + row_idx)
        
        # Load the target logit
        target_logit_ptr = logits_ptr + row_idx * logits_row_stride + target * logits_col_stride
        target_logit = tl.load(target_logit_ptr)
        
        # Find max for numerical stability
        row_start_ptr = logits_ptr + row_idx * logits_row_stride
        max_val = tl.full((1,), -float('inf'), dtype=tl.float32)
        
        for col_offset in range(0, N, BLOCK_SIZE):
            col_idx = col_offset + tl.arange(0, BLOCK_SIZE)
            mask = col_idx < N
            
            col_ptrs = row_start_ptr + col_idx * logits_col_stride
            logits_chunk = tl.load(col_ptrs, mask=mask, other=-float('inf'))
            chunk_max = tl.max(logits_chunk, axis=0)
            max_val = tl.maximum(max_val, chunk_max)
        
        # Compute log-sum-exp
        sum_exp = tl.full((1,), 0.0, dtype=tl.float32)
        
        for col_offset in range(0, N, BLOCK_SIZE):
            col_idx = col_offset + tl.arange(0, BLOCK_SIZE)
            mask = col_idx < N
            
            col_ptrs = row_start_ptr + col_idx * logits_col_stride
            logits_chunk = tl.load(col_ptrs, mask=mask, other=-float('inf'))
            exp_vals = tl.exp(logits_chunk - max_val)
            chunk_sum = tl.sum(exp_vals, axis=0)
            sum_exp += chunk_sum
        
        log_sum_exp = max_val + tl.log(sum_exp)
        
        # Compute loss: - (target_logit - log_sum_exp)
        loss = -(target_logit - log_sum_exp)
        
        tl.store(output_ptr + row_idx, loss)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024, 'NUM_ROWS_PER_PROGRAM': 1}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 128, 'NUM_ROWS_PER_PROGRAM': 2}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256, 'NUM_ROWS_PER_PROGRAM': 2}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'NUM_ROWS_PER_PROGRAM': 2}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_kernel_fast(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    logits_row_stride,
    logits_col_stride,
    BLOCK_SIZE: tl.constexpr,
    NUM_ROWS_PER_PROGRAM: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    row_start = pid * NUM_ROWS_PER_PROGRAM
    row_end = min(row_start + NUM_ROWS_PER_PROGRAM, M)
    
    for row_idx in range(row_start, row_end):
        target = tl.load(targets_ptr + row_idx)
        row_start_ptr = logits_ptr + row_idx * logits_row_stride
        
        # Find max and compute sum_exp in one pass
        max_val = tl.full((1,), -float('inf'), dtype=tl.float32)
        sum_exp = tl.full((1,), 0.0, dtype=tl.float32)
        target_logit = tl.full((1,), 0.0, dtype=tl.float32)
        
        for col_offset in range(0, N, BLOCK_SIZE):
            col_idx = col_offset + tl.arange(0, BLOCK_SIZE)
            mask = col_idx < N
            
            col_ptrs = row_start_ptr + col_idx * logits_col_stride
            logits_chunk = tl.load(col_ptrs, mask=mask, other=-float('inf'))
            
            # Track target logit
            target_mask = col_idx == target
            target_chunk = tl.where(target_mask, logits_chunk, 0.0)
            target_logit += tl.sum(target_chunk, axis=0)
            
            # Update max and sum_exp
            chunk_max = tl.max(logits_chunk, axis=0)
            new_max = tl.maximum(max_val, chunk_max)
            
            # Adjust sum_exp for max change
            if col_offset > 0:
                sum_exp *= tl.exp(max_val - new_max)
            
            max_val = new_max
            shifted = logits_chunk - max_val
            exp_vals = tl.exp(shifted)
            chunk_sum = tl.sum(exp_vals, axis=0)
            sum_exp += chunk_sum
        
        log_sum_exp = max_val + tl.log(sum_exp)
        loss = -(target_logit - log_sum_exp)
        
        tl.store(output_ptr + row_idx, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    assert logits.is_cuda and targets.is_cuda, "Tensors must be on GPU"
    assert logits.dtype == torch.float32, "Logits must be float32"
    assert targets.dtype == torch.int64, "Targets must be int64"
    assert targets.shape == (M,), f"Targets shape {targets.shape} != ({M},)"
    
    # Ensure contiguous memory layout
    if not logits.is_contiguous():
        logits = logits.contiguous()
    
    if not targets.is_contiguous():
        targets = targets.contiguous()
    
    # Choose kernel based on problem size
    if N >= 4096:
        grid = lambda META: (triton.cdiv(M, META['NUM_ROWS_PER_PROGRAM']),)
        _cross_entropy_kernel_fast[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
        )
    else:
        grid = lambda META: (triton.cdiv(M, META['NUM_ROWS_PER_PROGRAM']),)
        _cross_entropy_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
        )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__("inspect").getsource(__import__(__name__))}