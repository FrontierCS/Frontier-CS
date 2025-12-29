import torch
import triton
import triton.language as tl
import os
from typing import Optional


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512, 'STAGES': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 128, 'STAGES': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 256, 'STAGES': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 512, 'STAGES': 2}, num_warps=8),
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    STAGES: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    logits_block_ptr = tl.make_block_ptr(
        base=logits_ptr,
        shape=(M, N),
        strides=(stride_logits_m, stride_logits_n),
        offsets=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0)
    )
    
    logits = tl.load(logits_block_ptr, boundary_check=(0, 1))
    logits = tl.where(mask_m[:, None] & mask_n[None, :], logits, float('-inf'))
    
    row_max = tl.max(logits, axis=1)
    logits_minus_max = logits - row_max[:, None]
    
    exp_logits = tl.exp(logits_minus_max)
    row_sum_exp = tl.sum(exp_logits, axis=1)
    log_sum_exp = tl.log(row_sum_exp) + row_max
    
    targets = tl.load(targets_ptr + offs_m, mask=mask_m)
    target_idx = targets[:, None] - (pid_n * BLOCK_N)
    target_mask = (target_idx >= 0) & (target_idx < BLOCK_N) & mask_m[:, None]
    
    target_logits = tl.where(
        target_mask,
        tl.load(
            logits_ptr + offs_m[:, None] * stride_logits_m + target_idx * stride_logits_n,
            mask=target_mask,
            other=0.0
        ),
        0.0
    )
    
    target_logits = tl.sum(target_logits, axis=1)
    
    loss = log_sum_exp - target_logits
    
    tl.store(output_ptr + offs_m, loss, mask=mask_m)


@triton.jit
def cross_entropy_kernel_small(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    logits = tl.load(
        logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n,
        mask=mask_m[:, None] & mask_n[None, :],
        other=float('-inf')
    )
    
    row_max = tl.max(logits, axis=1)
    logits_minus_max = logits - row_max[:, None]
    
    exp_logits = tl.exp(logits_minus_max)
    row_sum_exp = tl.sum(exp_logits, axis=1)
    log_sum_exp = tl.log(row_sum_exp) + row_max
    
    targets = tl.load(targets_ptr + offs_m, mask=mask_m)
    
    target_logits = tl.load(
        logits_ptr + offs_m * stride_logits_m + targets * stride_logits_n,
        mask=mask_m,
        other=0.0
    )
    
    loss = log_sum_exp - target_logits
    
    tl.store(output_ptr + offs_m, loss, mask=mask_m)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    assert logits.size(0) == targets.size(0), "batch size mismatch"
    
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if N <= 4096:
        BLOCK_N = triton.next_power_of_2(N)
        BLOCK_M = 256 if M >= 256 else triton.next_power_of_2(M)
        
        grid = (triton.cdiv(M, BLOCK_M),)
        cross_entropy_kernel_small[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
        )
    else:
        BLOCK_M = 256
        BLOCK_N = 256
        
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        cross_entropy_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
        )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl
import os
from typing import Optional


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'STAGES': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512, 'STAGES': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 128, 'STAGES': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 256, 'STAGES': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 512, 'STAGES': 2}, num_warps=8),
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    STAGES: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    logits_block_ptr = tl.make_block_ptr(
        base=logits_ptr,
        shape=(M, N),
        strides=(stride_logits_m, stride_logits_n),
        offsets=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0)
    )
    
    logits = tl.load(logits_block_ptr, boundary_check=(0, 1))
    logits = tl.where(mask_m[:, None] & mask_n[None, :], logits, float('-inf'))
    
    row_max = tl.max(logits, axis=1)
    logits_minus_max = logits - row_max[:, None]
    
    exp_logits = tl.exp(logits_minus_max)
    row_sum_exp = tl.sum(exp_logits, axis=1)
    log_sum_exp = tl.log(row_sum_exp) + row_max
    
    targets = tl.load(targets_ptr + offs_m, mask=mask_m)
    target_idx = targets[:, None] - (pid_n * BLOCK_N)
    target_mask = (target_idx >= 0) & (target_idx < BLOCK_N) & mask_m[:, None]
    
    target_logits = tl.where(
        target_mask,
        tl.load(
            logits_ptr + offs_m[:, None] * stride_logits_m + target_idx * stride_logits_n,
            mask=target_mask,
            other=0.0
        ),
        0.0
    )
    
    target_logits = tl.sum(target_logits, axis=1)
    
    loss = log_sum_exp - target_logits
    
    tl.store(output_ptr + offs_m, loss, mask=mask_m)


@triton.jit
def cross_entropy_kernel_small(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_logits_m,
    stride_logits_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    logits = tl.load(
        logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n,
        mask=mask_m[:, None] & mask_n[None, :],
        other=float('-inf')
    )
    
    row_max = tl.max(logits, axis=1)
    logits_minus_max = logits - row_max[:, None]
    
    exp_logits = tl.exp(logits_minus_max)
    row_sum_exp = tl.sum(exp_logits, axis=1)
    log_sum_exp = tl.log(row_sum_exp) + row_max
    
    targets = tl.load(targets_ptr + offs_m, mask=mask_m)
    
    target_logits = tl.load(
        logits_ptr + offs_m * stride_logits_m + targets * stride_logits_n,
        mask=mask_m,
        other=0.0
    )
    
    loss = log_sum_exp - target_logits
    
    tl.store(output_ptr + offs_m, loss, mask=mask_m)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    assert logits.size(0) == targets.size(0), "batch size mismatch"
    
    M, N = logits.shape
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if N <= 4096:
        BLOCK_N = triton.next_power_of_2(N)
        BLOCK_M = 256 if M >= 256 else triton.next_power_of_2(M)
        
        grid = (triton.cdiv(M, BLOCK_M),)
        cross_entropy_kernel_small[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
        )
    else:
        BLOCK_M = 256
        BLOCK_N = 256
        
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        cross_entropy_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
        )
    
    return output
"""
        return {"code": code}