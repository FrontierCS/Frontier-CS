import torch
import triton
import triton.language as tl
from typing import Optional
import os

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 128}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 256}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    logits_stride_m,
    logits_stride_n,
    M,
    N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    off_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    off_m_mask = off_m < M
    off_n_mask = off_n < N
    
    logits_ptrs = logits_ptr + off_m[:, None] * logits_stride_m + off_n[None, :] * logits_stride_n
    logits_block = tl.load(logits_ptrs, mask=off_m_mask[:, None] & off_n_mask[None, :], other=-float('inf'))
    
    max_val = tl.max(logits_block, axis=1)
    exp_block = tl.exp(logits_block - max_val[:, None])
    sum_exp = tl.sum(exp_block, axis=1)
    log_sum_exp = tl.log(sum_exp) + max_val
    
    if pid_n == 0:
        target_ptrs = targets_ptr + off_m
        targets_block = tl.load(target_ptrs, mask=off_m_mask, other=0)
        
        target_mask = tl.arange(0, BLOCK_N)[None, :] == targets_block[:, None]
        target_logits = tl.sum(logits_block * target_mask, axis=1)
        
        loss = log_sum_exp - target_logits
        
        output_ptrs = output_ptr + off_m
        tl.store(output_ptrs, loss, mask=off_m_mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_small_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    logits_stride_m,
    logits_stride_n,
    M,
    N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    off_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    off_n = tl.arange(0, BLOCK_N)
    
    off_m_mask = off_m < M
    
    row_max = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    row_sum = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    target_logit = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        off_n_cur = n_start + off_n
        off_n_mask = off_n_cur < N
        
        logits_ptrs = logits_ptr + off_m[:, None] * logits_stride_m + off_n_cur[None, :] * logits_stride_n
        logits_block = tl.load(logits_ptrs, mask=off_m_mask[:, None] & off_n_mask[None, :], other=-float('inf'))
        
        if n_start == 0:
            target_ptrs = targets_ptr + off_m
            targets_block = tl.load(target_ptrs, mask=off_m_mask, other=0)
            target_mask = off_n_cur[None, :] == targets_block[:, None]
            target_logit += tl.sum(logits_block * target_mask, axis=1)
        else:
            target_mask = off_n_cur[None, :] == targets_block[:, None]
            target_logit += tl.sum(logits_block * target_mask, axis=1)
        
        block_max = tl.max(logits_block, axis=1)
        new_max = tl.maximum(row_max, block_max)
        
        exp_old = tl.exp(row_max - new_max)
        exp_new = tl.exp(logits_block - new_max[:, None])
        
        row_sum = row_sum * exp_old + tl.sum(exp_new, axis=1)
        row_max = new_max
    
    log_sum_exp = tl.log(row_sum) + row_max
    loss = log_sum_exp - target_logit
    
    output_ptrs = output_ptr + off_m
    tl.store(output_ptrs, loss, mask=off_m_mask)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if M == 0:
        return output
    
    if logits.stride(1) != 1:
        logits = logits.contiguous()
    if targets.stride(0) != 1:
        targets = targets.contiguous()
    
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    
    def grid_small(meta):
        return (triton.cdiv(M, meta['BLOCK_M']),)
    
    if N <= 16384:
        _cross_entropy_forward_small_kernel[grid_small](
            logits,
            targets,
            output,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
        )
    else:
        _cross_entropy_forward_kernel[grid](
            logits,
            targets,
            output,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(current_dir, "cross_entropy_kernel.py")
        
        code = '''import torch
import triton
import triton.language as tl
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 128}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 256}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    logits_stride_m,
    logits_stride_n,
    M,
    N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    off_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    off_m_mask = off_m < M
    off_n_mask = off_n < N
    
    logits_ptrs = logits_ptr + off_m[:, None] * logits_stride_m + off_n[None, :] * logits_stride_n
    logits_block = tl.load(logits_ptrs, mask=off_m_mask[:, None] & off_n_mask[None, :], other=-float('inf'))
    
    max_val = tl.max(logits_block, axis=1)
    exp_block = tl.exp(logits_block - max_val[:, None])
    sum_exp = tl.sum(exp_block, axis=1)
    log_sum_exp = tl.log(sum_exp) + max_val
    
    if pid_n == 0:
        target_ptrs = targets_ptr + off_m
        targets_block = tl.load(target_ptrs, mask=off_m_mask, other=0)
        
        target_mask = tl.arange(0, BLOCK_N)[None, :] == targets_block[:, None]
        target_logits = tl.sum(logits_block * target_mask, axis=1)
        
        loss = log_sum_exp - target_logits
        
        output_ptrs = output_ptr + off_m
        tl.store(output_ptrs, loss, mask=off_m_mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_small_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    logits_stride_m,
    logits_stride_n,
    M,
    N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    off_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    off_n = tl.arange(0, BLOCK_N)
    
    off_m_mask = off_m < M
    
    row_max = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    row_sum = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    target_logit = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        off_n_cur = n_start + off_n
        off_n_mask = off_n_cur < N
        
        logits_ptrs = logits_ptr + off_m[:, None] * logits_stride_m + off_n_cur[None, :] * logits_stride_n
        logits_block = tl.load(logits_ptrs, mask=off_m_mask[:, None] & off_n_mask[None, :], other=-float('inf'))
        
        if n_start == 0:
            target_ptrs = targets_ptr + off_m
            targets_block = tl.load(target_ptrs, mask=off_m_mask, other=0)
            target_mask = off_n_cur[None, :] == targets_block[:, None]
            target_logit += tl.sum(logits_block * target_mask, axis=1)
        else:
            target_mask = off_n_cur[None, :] == targets_block[:, None]
            target_logit += tl.sum(logits_block * target_mask, axis=1)
        
        block_max = tl.max(logits_block, axis=1)
        new_max = tl.maximum(row_max, block_max)
        
        exp_old = tl.exp(row_max - new_max)
        exp_new = tl.exp(logits_block - new_max[:, None])
        
        row_sum = row_sum * exp_old + tl.sum(exp_new, axis=1)
        row_max = new_max
    
    log_sum_exp = tl.log(row_sum) + row_max
    loss = log_sum_exp - target_logit
    
    output_ptrs = output_ptr + off_m
    tl.store(output_ptrs, loss, mask=off_m_mask)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if M == 0:
        return output
    
    if logits.stride(1) != 1:
        logits = logits.contiguous()
    if targets.stride(0) != 1:
        targets = targets.contiguous()
    
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    
    def grid_small(meta):
        return (triton.cdiv(M, meta['BLOCK_M']),)
    
    if N <= 16384:
        _cross_entropy_forward_small_kernel[grid_small](
            logits,
            targets,
            output,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
        )
    else:
        _cross_entropy_forward_kernel[grid](
            logits,
            targets,
            output,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
        )
    
    return output
'''
        
        with open(output_path, 'w') as f:
            f.write(code)
        
        return {"program_path": output_path}