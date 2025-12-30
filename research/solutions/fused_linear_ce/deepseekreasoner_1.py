import torch
import triton
import triton.language as tl


@triton.jit
def fused_linear_ce_kernel(
    X, W, B, targets, output,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_out,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    TWO_PASS: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_K) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        acc += tl.dot(x, w)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    if TWO_PASS:
        row_max = tl.max(acc, axis=1)
        tl.store(output + pid_m * BLOCK_M * stride_out + offs_n, row_max[:, None], mask=offs_n[None, :] < 1)
    else:
        b_ptrs = B + offs_n
        b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        acc += b[None, :]
        
        target_ptrs = targets + offs_m
        target = tl.load(target_ptrs, mask=offs_m < M, other=0)
        
        target_mask = target[:, None] == offs_n[None, :]
        target_logits = tl.sum(acc * target_mask, axis=1)
        
        row_max = tl.load(output + pid_m * BLOCK_M * stride_out)
        shifted = acc - row_max[:, None]
        exp_vals = tl.exp(shifted)
        sum_exp = tl.sum(exp_vals, axis=1)
        
        log_sum_exp = tl.log(sum_exp) + row_max
        loss = log_sum_exp - target_logits
        
        out_ptrs = output + offs_m * stride_out
        tl.store(out_ptrs, loss, mask=offs_m < M)


@triton.jit
def compute_loss_kernel(
    logits, row_max, targets, output,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_out,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    logits_ptrs = logits + (offs_m[:, None] * stride_logits_m + offs_n[None, :] * stride_logits_n)
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    logits_block = tl.load(logits_ptrs, mask=mask, other=0.0)
    
    row_max_vals = tl.load(row_max + offs_m, mask=offs_m < M, other=0.0)
    shifted = logits_block - row_max_vals[:, None]
    exp_vals = tl.exp(shifted)
    
    sum_exp = tl.sum(exp_vals, axis=1)
    
    target_ptrs = targets + offs_m
    target = tl.load(target_ptrs, mask=offs_m < M, other=0)
    target_mask = target[:, None] == offs_n[None, :]
    target_logits = tl.sum(logits_block * target_mask, axis=1)
    
    log_sum_exp = tl.log(sum_exp) + row_max_vals
    loss = log_sum_exp - target_logits
    
    out_ptrs = output + offs_m * stride_out
    tl.store(out_ptrs, loss, mask=offs_m < M)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    device = X.device
    
    BLOCK_M = 128 if M >= 512 else 64
    BLOCK_N = 128 if N >= 8192 else 64
    BLOCK_K = 64
    
    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)
    
    row_max = torch.empty((M,), device=device, dtype=torch.float32)
    output = torch.empty((M,), device=device, dtype=torch.float32)
    
    fused_linear_ce_kernel[(grid_m, grid_n)](
        X, W, B, targets, row_max,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        row_max.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        TWO_PASS=True,
    )
    
    fused_linear_ce_kernel[(grid_m, grid_n)](
        X, W, B, targets, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        TWO_PASS=False,
    )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.jit
def fused_linear_ce_kernel(
    X, W, B, targets, output,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_out,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    TWO_PASS: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_K) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        acc += tl.dot(x, w)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    if TWO_PASS:
        row_max = tl.max(acc, axis=1)
        tl.store(output + pid_m * BLOCK_M * stride_out + offs_n, row_max[:, None], mask=offs_n[None, :] < 1)
    else:
        b_ptrs = B + offs_n
        b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        acc += b[None, :]
        
        target_ptrs = targets + offs_m
        target = tl.load(target_ptrs, mask=offs_m < M, other=0)
        
        target_mask = target[:, None] == offs_n[None, :]
        target_logits = tl.sum(acc * target_mask, axis=1)
        
        row_max = tl.load(output + pid_m * BLOCK_M * stride_out)
        shifted = acc - row_max[:, None]
        exp_vals = tl.exp(shifted)
        sum_exp = tl.sum(exp_vals, axis=1)
        
        log_sum_exp = tl.log(sum_exp) + row_max
        loss = log_sum_exp - target_logits
        
        out_ptrs = output + offs_m * stride_out
        tl.store(out_ptrs, loss, mask=offs_m < M)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    device = X.device
    
    if M >= 512:
        BLOCK_M = 128
    elif M >= 256:
        BLOCK_M = 64
    else:
        BLOCK_M = 32
    
    if N >= 8192:
        BLOCK_N = 128
    elif N >= 4096:
        BLOCK_N = 64
    else:
        BLOCK_N = 32
    
    BLOCK_K = 64 if K >= 4096 else 32
    
    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)
    
    row_max = torch.empty((M,), device=device, dtype=torch.float32)
    output = torch.empty((M,), device=device, dtype=torch.float32)
    
    fused_linear_ce_kernel[(grid_m, grid_n)](
        X, W, B, targets, row_max,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        row_max.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        TWO_PASS=True,
    )
    
    fused_linear_ce_kernel[(grid_m, grid_n)](
        X, W, B, targets, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        TWO_PASS=False,
    )
    
    return output
"""
        return {"code": code}