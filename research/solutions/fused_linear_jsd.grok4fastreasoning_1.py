import torch
import triton
import triton.language as tl
import math
import inspect

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def fused_linear_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, L1_ptr, L2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1, stride_b2,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    rm = tl.arange(0, BLOCK_M)
    rn = tl.arange(0, BLOCK_N)
    offs_m = pid_m * BLOCK_M + rm
    offs_n = pid_n * BLOCK_N + rn
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    lo = 0
    hi = K
    while lo < hi:
        offs_k = lo + tl.arange(0, BLOCK_K)
        x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w1_ptrs = W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
        w1_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        w1 = tl.load(w1_ptrs, mask=w1_mask, other=0.0)
        acc1 += tl.dot(x, w1)
        w2_ptrs = W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
        w2_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        w2 = tl.load(w2_ptrs, mask=w2_mask, other=0.0)
        acc2 += tl.dot(x, w2)
        lo += BLOCK_K
    b1_ptrs = B1_ptr + offs_n * stride_b1
    b1_mask = offs_n < N
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    acc1 += tl.expand_dims(b1, 0)
    b2_ptrs = B2_ptr + offs_n * stride_b2
    b2_mask = offs_n < N
    b2 = tl.load(b2_ptrs, mask=b2_mask, other=0.0)
    acc2 += tl.expand_dims(b2, 0)
    l1_ptrs = L1_ptr + offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n
    l1_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(l1_ptrs, acc1, mask=l1_mask)
    l2_ptrs = L2_ptr + offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n
    l2_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(l2_ptrs, acc2, mask=l2_mask)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    L1 = torch.empty((M, N), dtype=torch.float32, device=X.device)
    L2 = torch.empty((M, N), dtype=torch.float32, device=X.device)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    fused_linear_kernel[grid](
        X, W1, B1, W2, B2, L1, L2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
    )
    log_p = torch.log_softmax(L1, dim=1)
    log_q = torch.log_softmax(L2, dim=1)
    log_half = math.log(0.5)
    max_log = torch.maximum(log_p, log_q)
    sum_exp = torch.exp(log_p - max_log) + torch.exp(log_q - max_log)
    log_sum_exp = max_log + torch.log(sum_exp)
    log_m = log_half + log_sum_exp
    exp_log_p = torch.exp(log_p)
    kl_p = torch.sum(exp_log_p * (log_p - log_m), dim=1)
    exp_log_q = torch.exp(log_q)
    kl_q = torch.sum(exp_log_q * (log_q - log_m), dim=1)
    jsd = 0.5 * (kl_p + kl_q)
    return jsd
"""
        return {"code": code}