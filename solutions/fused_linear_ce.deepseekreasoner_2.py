import torch
import triton
import triton.language as tl
import numpy as np
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_warps=2),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptr, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptr, mask=mask_w, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
        X_ptr += BLOCK_SIZE_K * stride_xk
        W_ptr += BLOCK_SIZE_K * stride_wk
    
    B_ptr += offs_n * stride_bn
    bias = tl.load(B_ptr, mask=offs_n < N, other=0.0)
    acc += bias[None, :]
    
    row_max = tl.max(acc, axis=1)
    row_sumexp = tl.sum(tl.exp(acc - row_max[:, None]), axis=1)
    log_sumexp = row_max + tl.log(row_sumexp)
    
    targets_ptr += offs_m * 1
    target_mask = offs_m < M
    target_idx = tl.load(targets_ptr, mask=target_mask, other=0)
    
    col_indices = target_idx[:, None]
    row_indices = tl.arange(0, BLOCK_SIZE_M)[:, None]
    target_logit_ptr = acc + row_indices * BLOCK_SIZE_N + col_indices
    target_logit = tl.load(target_logit_ptr, mask=target_mask[:, None] & (col_indices < BLOCK_SIZE_N), other=0.0)
    
    loss = log_sumexp - target_logit[:, 0]
    
    output_ptr += offs_m * stride_out_m
    tl.store(output_ptr, loss, mask=target_mask)

@triton.jit
def fused_linear_ce_kernel_small_n(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_SIZE_M, N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptr, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptr, mask=mask_w, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
        X_ptr += BLOCK_SIZE_K * stride_xk
        W_ptr += BLOCK_SIZE_K * stride_wk
    
    B_ptr += offs_n * stride_bn
    bias = tl.load(B_ptr, mask=offs_n < N, other=0.0)
    acc += bias[None, :]
    
    row_max = tl.max(acc, axis=1)
    row_sumexp = tl.sum(tl.exp(acc - row_max[:, None]), axis=1)
    log_sumexp = row_max + tl.log(row_sumexp)
    
    targets_ptr += offs_m * 1
    target_mask = offs_m < M
    target_idx = tl.load(targets_ptr, mask=target_mask, other=0)
    
    col_indices = target_idx[:, None]
    row_indices = tl.arange(0, BLOCK_SIZE_M)[:, None]
    target_logit = tl.load(acc + row_indices * N + col_indices, 
                          mask=target_mask[:, None], other=0.0)
    
    loss = log_sumexp - target_logit[:, 0]
    
    output_ptr += offs_m * stride_out_m
    tl.store(output_ptr, loss, mask=target_mask)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    grid = lambda meta: (
        triton.cdiv(M, meta['BLOCK_SIZE_M']),
        triton.cdiv(N, meta['BLOCK_SIZE_N']) if 'BLOCK_SIZE_N' in meta else 1,
    )
    
    if N <= 256:
        fused_linear_ce_kernel_small_n[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            output.stride(0),
            BLOCK_SIZE_M=min(128, triton.next_power_of_2(M)),
            BLOCK_SIZE_K=32,
        )
    else:
        fused_linear_ce_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            output.stride(0),
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import numpy as np
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_warps=2),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptr, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptr, mask=mask_w, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
        X_ptr += BLOCK_SIZE_K * stride_xk
        W_ptr += BLOCK_SIZE_K * stride_wk
    
    B_ptr += offs_n * stride_bn
    bias = tl.load(B_ptr, mask=offs_n < N, other=0.0)
    acc += bias[None, :]
    
    row_max = tl.max(acc, axis=1)
    row_sumexp = tl.sum(tl.exp(acc - row_max[:, None]), axis=1)
    log_sumexp = row_max + tl.log(row_sumexp)
    
    targets_ptr += offs_m * 1
    target_mask = offs_m < M
    target_idx = tl.load(targets_ptr, mask=target_mask, other=0)
    
    col_indices = target_idx[:, None]
    row_indices = tl.arange(0, BLOCK_SIZE_M)[:, None]
    target_logit_ptr = acc + row_indices * BLOCK_SIZE_N + col_indices
    target_logit = tl.load(target_logit_ptr, mask=target_mask[:, None] & (col_indices < BLOCK_SIZE_N), other=0.0)
    
    loss = log_sumexp - target_logit[:, 0]
    
    output_ptr += offs_m * stride_out_m
    tl.store(output_ptr, loss, mask=target_mask)

@triton.jit
def fused_linear_ce_kernel_small_n(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_SIZE_M, N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptr, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptr, mask=mask_w, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
        X_ptr += BLOCK_SIZE_K * stride_xk
        W_ptr += BLOCK_SIZE_K * stride_wk
    
    B_ptr += offs_n * stride_bn
    bias = tl.load(B_ptr, mask=offs_n < N, other=0.0)
    acc += bias[None, :]
    
    row_max = tl.max(acc, axis=1)
    row_sumexp = tl.sum(tl.exp(acc - row_max[:, None]), axis=1)
    log_sumexp = row_max + tl.log(row_sumexp)
    
    targets_ptr += offs_m * 1
    target_mask = offs_m < M
    target_idx = tl.load(targets_ptr, mask=target_mask, other=0)
    
    col_indices = target_idx[:, None]
    row_indices = tl.arange(0, BLOCK_SIZE_M)[:, None]
    target_logit = tl.load(acc + row_indices * N + col_indices, 
                          mask=target_mask[:, None], other=0.0)
    
    loss = log_sumexp - target_logit[:, 0]
    
    output_ptr += offs_m * stride_out_m
    tl.store(output_ptr, loss, mask=target_mask)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    grid = lambda meta: (
        triton.cdiv(M, meta['BLOCK_SIZE_M']),
        triton.cdiv(N, meta['BLOCK_SIZE_N']) if 'BLOCK_SIZE_N' in meta else 1,
    )
    
    if N <= 256:
        fused_linear_ce_kernel_small_n[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            output.stride(0),
            BLOCK_SIZE_M=min(128, triton.next_power_of_2(M)),
            BLOCK_SIZE_K=32,
        )
    else:
        fused_linear_ce_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            output.stride(0),
        )
    
    return output
"""
        return {"code": code}
