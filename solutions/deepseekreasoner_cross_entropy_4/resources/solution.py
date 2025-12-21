import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256}, num_warps=16),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 512}, num_warps=16),
    ],
    key=['M', 'N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    stride_logits_m,
    stride_logits_n,
    M,
    N,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    pid_m = pid // tl.cdiv(N, BLOCK_SIZE_N)
    pid_n = pid % tl.cdiv(N, BLOCK_SIZE_N)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    logits_block_ptr = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
    logits = tl.load(logits_block_ptr, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
    
    row_max = tl.max(logits, axis=1)
    logits = logits - row_max[:, None]
    exp_logits = tl.exp(logits)
    row_sum = tl.sum(exp_logits, axis=1)
    log_softmax = logits - tl.log(row_sum[:, None])
    
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    target_mask = tl.where(offs_n[None, :] == targets[:, None], 1, 0)
    
    selected = tl.sum(log_softmax * target_mask, axis=1)
    loss = -selected
    
    tl.store(loss_ptr + offs_m, loss, mask=mask_m)

@triton.jit
def cross_entropy_kernel_small(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    stride_logits_m,
    stride_logits_n,
    M,
    N,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    offs_m = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask_m = offs_m < M
    
    logits_row_ptr = logits_ptr + offs_m * stride_logits_m
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    
    row_max = tl.zeros([BLOCK_SIZE], dtype=tl.float32) - float('inf')
    row_sum = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
    
    for i in range(0, N, BLOCK_SIZE):
        offs_n = i + tl.arange(0, BLOCK_SIZE)
        mask_n = offs_n < N
        
        logits = tl.load(logits_row_ptr + offs_n[None, :] * stride_logits_n, 
                        mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
        
        new_max = tl.maximum(row_max, tl.max(logits, axis=1))
        exp_adj = tl.exp(row_max - new_max)
        row_sum = row_sum * exp_adj + tl.sum(tl.exp(logits - new_max[:, None]), axis=1)
        row_max = new_max
    
    target_logits = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
    for i in range(0, N, BLOCK_SIZE):
        offs_n = i + tl.arange(0, BLOCK_SIZE)
        mask_n = offs_n < N
        
        logits = tl.load(logits_row_ptr + offs_n[None, :] * stride_logits_n,
                        mask=mask_m[:, None] & mask_n[None, :], other=0.0)
        
        target_mask = tl.where(offs_n[None, :] == targets[:, None], 1, 0)
        target_logits += tl.sum(logits * target_mask, axis=1)
    
    loss = -(target_logits - row_max - tl.log(row_sum))
    tl.store(loss_ptr + offs_m, loss, mask=mask_m)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    assert logits.shape[0] == targets.shape[0], "batch size mismatch"
    
    M, N = logits.shape
    loss = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if M < 128 or N < 512:
        BLOCK_SIZE = triton.next_power_of_2(min(128, M))
        grid = (triton.cdiv(M, BLOCK_SIZE),)
        cross_entropy_kernel_small[grid](
            logits,
            targets,
            loss,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
            BLOCK_SIZE=BLOCK_SIZE,
        )
    else:
        grid = (triton.cdiv(M, 64) * triton.cdiv(N, 128),)
        cross_entropy_kernel[grid](
            logits,
            targets,
            loss,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
        )
    
    return loss

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256}, num_warps=16),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 512}, num_warps=16),
    ],
    key=['M', 'N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    stride_logits_m,
    stride_logits_n,
    M,
    N,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    pid_m = pid // tl.cdiv(N, BLOCK_SIZE_N)
    pid_n = pid % tl.cdiv(N, BLOCK_SIZE_N)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    logits_block_ptr = logits_ptr + offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n
    logits = tl.load(logits_block_ptr, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
    
    row_max = tl.max(logits, axis=1)
    logits = logits - row_max[:, None]
    exp_logits = tl.exp(logits)
    row_sum = tl.sum(exp_logits, axis=1)
    log_softmax = logits - tl.log(row_sum[:, None])
    
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    target_mask = tl.where(offs_n[None, :] == targets[:, None], 1, 0)
    
    selected = tl.sum(log_softmax * target_mask, axis=1)
    loss = -selected
    
    tl.store(loss_ptr + offs_m, loss, mask=mask_m)

@triton.jit
def cross_entropy_kernel_small(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    stride_logits_m,
    stride_logits_n,
    M,
    N,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    offs_m = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask_m = offs_m < M
    
    logits_row_ptr = logits_ptr + offs_m * stride_logits_m
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
    
    row_max = tl.zeros([BLOCK_SIZE], dtype=tl.float32) - float('inf')
    row_sum = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
    
    for i in range(0, N, BLOCK_SIZE):
        offs_n = i + tl.arange(0, BLOCK_SIZE)
        mask_n = offs_n < N
        
        logits = tl.load(logits_row_ptr + offs_n[None, :] * stride_logits_n, 
                        mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
        
        new_max = tl.maximum(row_max, tl.max(logits, axis=1))
        exp_adj = tl.exp(row_max - new_max)
        row_sum = row_sum * exp_adj + tl.sum(tl.exp(logits - new_max[:, None]), axis=1)
        row_max = new_max
    
    target_logits = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
    for i in range(0, N, BLOCK_SIZE):
        offs_n = i + tl.arange(0, BLOCK_SIZE)
        mask_n = offs_n < N
        
        logits = tl.load(logits_row_ptr + offs_n[None, :] * stride_logits_n,
                        mask=mask_m[:, None] & mask_n[None, :], other=0.0)
        
        target_mask = tl.where(offs_n[None, :] == targets[:, None], 1, 0)
        target_logits += tl.sum(logits * target_mask, axis=1)
    
    loss = -(target_logits - row_max - tl.log(row_sum))
    tl.store(loss_ptr + offs_m, loss, mask=mask_m)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    assert logits.shape[0] == targets.shape[0], "batch size mismatch"
    
    M, N = logits.shape
    loss = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if M < 128 or N < 512:
        BLOCK_SIZE = triton.next_power_of_2(min(128, M))
        grid = (triton.cdiv(M, BLOCK_SIZE),)
        cross_entropy_kernel_small[grid](
            logits,
            targets,
            loss,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
            BLOCK_SIZE=BLOCK_SIZE,
        )
    else:
        grid = (triton.cdiv(M, 64) * triton.cdiv(N, 128),)
        cross_entropy_kernel[grid](
            logits,
            targets,
            loss,
            logits.stride(0),
            logits.stride(1),
            M,
            N,
        )
    
    return loss
"""
        return {"code": code}
