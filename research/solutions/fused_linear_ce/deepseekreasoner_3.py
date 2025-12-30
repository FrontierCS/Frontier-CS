import torch
import triton
import triton.language as tl
import os

@triton.jit
def _fused_linear_ce_forward_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    USE_TWO_PASS: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = min(BLOCK_K, K - k)
        if k_remaining < BLOCK_K:
            mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < k_remaining)
            mask_w = (offs_k[:, None] < k_remaining) & (offs_n[None, :] < N)
            x = tl.load(x_ptrs, mask=mask_x, other=0.0)
            w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        else:
            mask_x = offs_m[:, None] < M
            mask_w = offs_n[None, :] < N
            x = tl.load(x_ptrs, mask=mask_x, other=0.0)
            w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        x_f32 = x.to(tl.float32)
        w_f32 = w.to(tl.float32)
        acc += tl.dot(x_f32, w_f32)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    if USE_TWO_PASS:
        row_max = tl.max(acc, axis=1)
        
        exp_acc = tl.exp(acc - row_max[:, None])
        row_sumexp = tl.sum(exp_acc, axis=1)
        
        if pid_n == 0:
            targets = tl.load(targets_ptr + offs_m, mask=offs_m < M, other=0)
            target_mask = (offs_n[None, :] == targets[:, None]) & (offs_m[:, None] < M)
            target_logits = tl.sum(acc * target_mask.to(tl.float32), axis=1)
            
            log_sumexp = tl.log(row_sumexp) + row_max
            loss = log_sumexp - target_logits
            
            out_ptrs = output_ptr + offs_m * stride_out_m
            tl.store(out_ptrs, loss, mask=offs_m < M)

@triton.jit
def _fused_linear_ce_optimized_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = min(BLOCK_K, K - k)
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < k_remaining)
        mask_w = (offs_k[:, None] < k_remaining) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        acc += tl.dot(x.to(tl.float32), w.to(tl.float32))
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    b_ptrs = B_ptr + offs_n * stride_bn
    bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0).to(tl.float32)
    acc += bias[None, :]
    
    if pid_n == 0:
        targets = tl.load(targets_ptr + offs_m, mask=offs_m < M, other=0)
        target_mask = (offs_n[None, :] == targets[:, None]) & (offs_m[:, None] < M)
        target_logits = tl.sum(acc * target_mask.to(tl.float32), axis=1)
    
    row_max = tl.max(acc, axis=1)
    
    exp_acc = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_acc, axis=1)
    
    if pid_n == 0:
        log_sumexp = tl.log(row_sumexp) + row_max
        loss = log_sumexp - target_logits
        
        out_ptrs = output_ptr + offs_m * stride_out_m
        tl.store(out_ptrs, loss, mask=offs_m < M)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    
    if M >= 512:
        BLOCK_M = 128
        BLOCK_N = 256
        BLOCK_K = 64
    elif M >= 256:
        BLOCK_M = 64
        BLOCK_N = 256
        BLOCK_K = 64
    else:
        BLOCK_M = 32
        BLOCK_N = 256
        BLOCK_K = 64
    
    kernel = _fused_linear_ce_optimized_kernel
    kernel[grid](
        X, W, B, targets, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def _fused_linear_ce_forward_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    USE_TWO_PASS: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = min(BLOCK_K, K - k)
        if k_remaining < BLOCK_K:
            mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < k_remaining)
            mask_w = (offs_k[:, None] < k_remaining) & (offs_n[None, :] < N)
            x = tl.load(x_ptrs, mask=mask_x, other=0.0)
            w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        else:
            mask_x = offs_m[:, None] < M
            mask_w = offs_n[None, :] < N
            x = tl.load(x_ptrs, mask=mask_x, other=0.0)
            w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        x_f32 = x.to(tl.float32)
        w_f32 = w.to(tl.float32)
        acc += tl.dot(x_f32, w_f32)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    if USE_TWO_PASS:
        row_max = tl.max(acc, axis=1)
        
        exp_acc = tl.exp(acc - row_max[:, None])
        row_sumexp = tl.sum(exp_acc, axis=1)
        
        if pid_n == 0:
            targets = tl.load(targets_ptr + offs_m, mask=offs_m < M, other=0)
            target_mask = (offs_n[None, :] == targets[:, None]) & (offs_m[:, None] < M)
            target_logits = tl.sum(acc * target_mask.to(tl.float32), axis=1)
            
            log_sumexp = tl.log(row_sumexp) + row_max
            loss = log_sumexp - target_logits
            
            out_ptrs = output_ptr + offs_m * stride_out_m
            tl.store(out_ptrs, loss, mask=offs_m < M)

@triton.jit
def _fused_linear_ce_optimized_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = min(BLOCK_K, K - k)
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < k_remaining)
        mask_w = (offs_k[:, None] < k_remaining) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        acc += tl.dot(x.to(tl.float32), w.to(tl.float32))
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    b_ptrs = B_ptr + offs_n * stride_bn
    bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0).to(tl.float32)
    acc += bias[None, :]
    
    if pid_n == 0:
        targets = tl.load(targets_ptr + offs_m, mask=offs_m < M, other=0)
        target_mask = (offs_n[None, :] == targets[:, None]) & (offs_m[:, None] < M)
        target_logits = tl.sum(acc * target_mask.to(tl.float32), axis=1)
    
    row_max = tl.max(acc, axis=1)
    
    exp_acc = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_acc, axis=1)
    
    if pid_n == 0:
        log_sumexp = tl.log(row_sumexp) + row_max
        loss = log_sumexp - target_logits
        
        out_ptrs = output_ptr + offs_m * stride_out_m
        tl.store(out_ptrs, loss, mask=offs_m < M)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    
    if M >= 512:
        BLOCK_M = 128
        BLOCK_N = 256
        BLOCK_K = 64
    elif M >= 256:
        BLOCK_M = 64
        BLOCK_N = 256
        BLOCK_K = 64
    else:
        BLOCK_M = 32
        BLOCK_N = 256
        BLOCK_K = 64
    
    kernel = _fused_linear_ce_optimized_kernel
    kernel[grid](
        X, W, B, targets, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    
    return output'''
        
        return {"code": code}