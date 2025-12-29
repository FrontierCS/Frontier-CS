import torch
import triton
import triton.language as tl
import math


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 1024}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    stride_output_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = offs_m < M
    
    max_logit = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    sum_exp = tl.full((BLOCK_SIZE_M,), 0.0, dtype=tl.float32)
    target_logit = tl.full((BLOCK_SIZE_M,), 0.0, dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_end = min(n_start + BLOCK_SIZE_N, N)
        n_size = n_end - n_start
        
        logits_ptrs = (
            logits_ptr + 
            offs_m[:, None] * stride_logits_m + 
            (n_start + offs_n[None, :]) * stride_logits_n
        )
        mask = mask_m[:, None] & (offs_n[None, :] < n_size)
        
        logits_chunk = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
        
        chunk_max = tl.max(logits_chunk, axis=1)
        max_logit = tl.maximum(max_logit, chunk_max)
        
        exp_values = tl.exp(logits_chunk - max_logit[:, None])
        sum_exp += tl.sum(exp_values, axis=1)
        
        if n_start == 0:
            target_indices = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
        
        target_mask = (offs_n[None, :] == (target_indices[:, None] - n_start)) & mask
        target_chunk = tl.load(logits_ptrs, mask=target_mask, other=0.0)
        target_logit += tl.sum(target_chunk, axis=1)
    
    log_sum_exp = tl.log(sum_exp) + max_logit
    loss = log_sum_exp - target_logit
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    tl.store(output_ptrs, loss, mask=mask_m)


@triton.jit
def cross_entropy_kernel_small_n(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    stride_output_m,
    BLOCK_SIZE_M: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, 32)
    
    mask_m = offs_m < M
    
    logits_ptrs = (
        logits_ptr + 
        offs_m[:, None] * stride_logits_m + 
        offs_n[None, :] * stride_logits_n
    )
    mask = mask_m[:, None] & (offs_n[None, :] < N)
    
    logits = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
    
    max_logit = tl.max(logits, axis=1)
    exp_values = tl.exp(logits - max_logit[:, None])
    sum_exp = tl.sum(exp_values, axis=1)
    log_sum_exp = tl.log(sum_exp) + max_logit
    
    target_indices = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    target_mask = (offs_n[None, :] == target_indices[:, None]) & mask
    target_logit = tl.sum(tl.load(logits_ptrs, mask=target_mask, other=0.0), axis=1)
    
    loss = log_sum_exp - target_logit
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    tl.store(output_ptrs, loss, mask=mask_m)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D tensor"
    assert targets.dim() == 1, "targets must be 1D tensor"
    assert logits.size(0) == targets.size(0), "Batch size mismatch"
    
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if N <= 32:
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_SIZE_M']),)
        cross_entropy_kernel_small_n[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=64,
        )
    else:
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_SIZE_M']),)
        cross_entropy_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            output.stride(0),
        )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl
import math


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 1024}, num_warps=8),
    ],
    key=['M', 'N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    stride_output_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = offs_m < M
    
    max_logit = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    sum_exp = tl.full((BLOCK_SIZE_M,), 0.0, dtype=tl.float32)
    target_logit = tl.full((BLOCK_SIZE_M,), 0.0, dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_end = min(n_start + BLOCK_SIZE_N, N)
        n_size = n_end - n_start
        
        logits_ptrs = (
            logits_ptr + 
            offs_m[:, None] * stride_logits_m + 
            (n_start + offs_n[None, :]) * stride_logits_n
        )
        mask = mask_m[:, None] & (offs_n[None, :] < n_size)
        
        logits_chunk = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
        
        chunk_max = tl.max(logits_chunk, axis=1)
        max_logit = tl.maximum(max_logit, chunk_max)
        
        exp_values = tl.exp(logits_chunk - max_logit[:, None])
        sum_exp += tl.sum(exp_values, axis=1)
        
        if n_start == 0:
            target_indices = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
        
        target_mask = (offs_n[None, :] == (target_indices[:, None] - n_start)) & mask
        target_chunk = tl.load(logits_ptrs, mask=target_mask, other=0.0)
        target_logit += tl.sum(target_chunk, axis=1)
    
    log_sum_exp = tl.log(sum_exp) + max_logit
    loss = log_sum_exp - target_logit
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    tl.store(output_ptrs, loss, mask=mask_m)


@triton.jit
def cross_entropy_kernel_small_n(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    stride_output_m,
    BLOCK_SIZE_M: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, 32)
    
    mask_m = offs_m < M
    
    logits_ptrs = (
        logits_ptr + 
        offs_m[:, None] * stride_logits_m + 
        offs_n[None, :] * stride_logits_n
    )
    mask = mask_m[:, None] & (offs_n[None, :] < N)
    
    logits = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
    
    max_logit = tl.max(logits, axis=1)
    exp_values = tl.exp(logits - max_logit[:, None])
    sum_exp = tl.sum(exp_values, axis=1)
    log_sum_exp = tl.log(sum_exp) + max_logit
    
    target_indices = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    target_mask = (offs_n[None, :] == target_indices[:, None]) & mask
    target_logit = tl.sum(tl.load(logits_ptrs, mask=target_mask, other=0.0), axis=1)
    
    loss = log_sum_exp - target_logit
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    tl.store(output_ptrs, loss, mask=mask_m)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D tensor"
    assert targets.dim() == 1, "targets must be 1D tensor"
    assert logits.size(0) == targets.size(0), "Batch size mismatch"
    
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if N <= 32:
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_SIZE_M']),)
        cross_entropy_kernel_small_n[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=64,
        )
    else:
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_SIZE_M']),)
        cross_entropy_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            output.stride(0),
        )
    
    return output
"""}