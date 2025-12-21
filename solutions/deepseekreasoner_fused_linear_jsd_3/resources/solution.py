import torch
import triton
import triton.language as tl
from typing import Optional
import math

@triton.jit
def _fused_linear_jsd_kernel_pass1(
    X, W1, W2, B1, B2, M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    log_sum_exp1, log_sum_exp2,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W1_ptrs = W1 + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    W2_ptrs = W2 + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
    
    accumulator1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    accumulator2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_remaining = K - k
        k_mask = offs_k < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask[None, :] & (offs_m[:, None] < M), other=0.0)
        w1 = tl.load(W1_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        w2 = tl.load(W2_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        
        accumulator1 += tl.dot(x, w1, allow_tf32=False)
        accumulator2 += tl.dot(x, w2, allow_tf32=False)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W1_ptrs += BLOCK_SIZE_K * stride_w1k
        W2_ptrs += BLOCK_SIZE_K * stride_w2k
    
    if BLOCK_SIZE_N == 1:
        b1 = tl.load(B1 + offs_n, mask=offs_n < N)
        b2 = tl.load(B2 + offs_n, mask=offs_n < N)
        accumulator1 += b1[None, :]
        accumulator2 += b2[None, :]
    
    m1 = tl.max(accumulator1, 1)
    m2 = tl.max(accumulator2, 1)
    
    exp1 = tl.exp(accumulator1 - m1[:, None])
    exp2 = tl.exp(accumulator2 - m2[:, None])
    
    sum1 = tl.sum(exp1, 1)
    sum2 = tl.sum(exp2, 1)
    
    lse1 = m1 + tl.log(sum1)
    lse2 = m2 + tl.log(sum2)
    
    out_ptrs1 = log_sum_exp1 + offs_m
    out_ptrs2 = log_sum_exp2 + offs_m
    tl.store(out_ptrs1, lse1, mask=offs_m < M)
    tl.store(out_ptrs2, lse2, mask=offs_m < M)

@triton.jit
def _fused_linear_jsd_kernel_pass2(
    X, W1, W2, B1, B2, M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    log_sum_exp1, log_sum_exp2,
    output,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W1_ptrs = W1 + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    W2_ptrs = W2 + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
    
    accumulator1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    accumulator2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_remaining = K - k
        k_mask = offs_k < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask[None, :] & (offs_m[:, None] < M), other=0.0)
        w1 = tl.load(W1_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        w2 = tl.load(W2_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        
        accumulator1 += tl.dot(x, w1, allow_tf32=False)
        accumulator2 += tl.dot(x, w2, allow_tf32=False)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W1_ptrs += BLOCK_SIZE_K * stride_w1k
        W2_ptrs += BLOCK_SIZE_K * stride_w2k
    
    if BLOCK_SIZE_N == 1:
        b1 = tl.load(B1 + offs_n, mask=offs_n < N)
        b2 = tl.load(B2 + offs_n, mask=offs_n < N)
        accumulator1 += b1[None, :]
        accumulator2 += b2[None, :]
    
    lse1 = tl.load(log_sum_exp1 + offs_m, mask=offs_m < M)
    lse2 = tl.load(log_sum_exp2 + offs_m, mask=offs_m < M)
    
    log_p = accumulator1 - lse1[:, None]
    log_q = accumulator2 - lse2[:, None]
    
    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    m = 0.5 * (p + q)
    
    log_m = tl.log(m)
    
    kl_pm = tl.where(m > 0, p * (log_p - log_m), 0.0)
    kl_qm = tl.where(m > 0, q * (log_q - log_m), 0.0)
    
    jsd_contrib = 0.5 * (kl_pm + kl_qm)
    jsd_block = tl.sum(jsd_contrib, 1)
    
    out_ptrs = output + offs_m
    tl.atomic_add(out_ptrs, jsd_block, mask=offs_m < M)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                     W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    
    device = X.device
    
    log_sum_exp1 = torch.empty(M, dtype=torch.float32, device=device)
    log_sum_exp2 = torch.empty(M, dtype=torch.float32, device=device)
    output = torch.zeros(M, dtype=torch.float32, device=device)
    
    def get_config(M, N, K):
        if M <= 128:
            BLOCK_SIZE_M = 32
            BLOCK_SIZE_N = 64
            BLOCK_SIZE_K = 64
            GROUP_SIZE_M = 4
        else:
            BLOCK_SIZE_M = 64
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 64
            GROUP_SIZE_M = 4
        
        num_warps = 4
        if BLOCK_SIZE_N >= 128:
            num_warps = 8
        elif BLOCK_SIZE_N >= 256:
            num_warps = 16
        
        return {
            'BLOCK_SIZE_M': BLOCK_SIZE_M,
            'BLOCK_SIZE_N': BLOCK_SIZE_N,
            'BLOCK_SIZE_K': BLOCK_SIZE_K,
            'GROUP_SIZE_M': GROUP_SIZE_M,
            'num_warps': num_warps
        }
    
    config = get_config(M, N, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), 
    )
    
    # Pass 1: Compute log-sum-exp
    _fused_linear_jsd_kernel_pass1[grid](
        X, W1, W2, B1, B2, M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        log_sum_exp1, log_sum_exp2,
        **config
    )
    
    # Reset output for atomic accumulation
    output.zero_()
    
    # Pass 2: Compute JSD
    _fused_linear_jsd_kernel_pass2[grid](
        X, W1, W2, B1, B2, M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        log_sum_exp1, log_sum_exp2,
        output,
        **config
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
from typing import Optional
import math

@triton.jit
def _fused_linear_jsd_kernel_pass1(
    X, W1, W2, B1, B2, M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    log_sum_exp1, log_sum_exp2,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W1_ptrs = W1 + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    W2_ptrs = W2 + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
    
    accumulator1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    accumulator2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_remaining = K - k
        k_mask = offs_k < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask[None, :] & (offs_m[:, None] < M), other=0.0)
        w1 = tl.load(W1_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        w2 = tl.load(W2_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        
        accumulator1 += tl.dot(x, w1, allow_tf32=False)
        accumulator2 += tl.dot(x, w2, allow_tf32=False)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W1_ptrs += BLOCK_SIZE_K * stride_w1k
        W2_ptrs += BLOCK_SIZE_K * stride_w2k
    
    if BLOCK_SIZE_N == 1:
        b1 = tl.load(B1 + offs_n, mask=offs_n < N)
        b2 = tl.load(B2 + offs_n, mask=offs_n < N)
        accumulator1 += b1[None, :]
        accumulator2 += b2[None, :]
    
    m1 = tl.max(accumulator1, 1)
    m2 = tl.max(accumulator2, 1)
    
    exp1 = tl.exp(accumulator1 - m1[:, None])
    exp2 = tl.exp(accumulator2 - m2[:, None])
    
    sum1 = tl.sum(exp1, 1)
    sum2 = tl.sum(exp2, 1)
    
    lse1 = m1 + tl.log(sum1)
    lse2 = m2 + tl.log(sum2)
    
    out_ptrs1 = log_sum_exp1 + offs_m
    out_ptrs2 = log_sum_exp2 + offs_m
    tl.store(out_ptrs1, lse1, mask=offs_m < M)
    tl.store(out_ptrs2, lse2, mask=offs_m < M)

@triton.jit
def _fused_linear_jsd_kernel_pass2(
    X, W1, W2, B1, B2, M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    log_sum_exp1, log_sum_exp2,
    output,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W1_ptrs = W1 + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    W2_ptrs = W2 + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
    
    accumulator1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    accumulator2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_remaining = K - k
        k_mask = offs_k < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask[None, :] & (offs_m[:, None] < M), other=0.0)
        w1 = tl.load(W1_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        w2 = tl.load(W2_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        
        accumulator1 += tl.dot(x, w1, allow_tf32=False)
        accumulator2 += tl.dot(x, w2, allow_tf32=False)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W1_ptrs += BLOCK_SIZE_K * stride_w1k
        W2_ptrs += BLOCK_SIZE_K * stride_w2k
    
    if BLOCK_SIZE_N == 1:
        b1 = tl.load(B1 + offs_n, mask=offs_n < N)
        b2 = tl.load(B2 + offs_n, mask=offs_n < N)
        accumulator1 += b1[None, :]
        accumulator2 += b2[None, :]
    
    lse1 = tl.load(log_sum_exp1 + offs_m, mask=offs_m < M)
    lse2 = tl.load(log_sum_exp2 + offs_m, mask=offs_m < M)
    
    log_p = accumulator1 - lse1[:, None]
    log_q = accumulator2 - lse2[:, None]
    
    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    m = 0.5 * (p + q)
    
    log_m = tl.log(m)
    
    kl_pm = tl.where(m > 0, p * (log_p - log_m), 0.0)
    kl_qm = tl.where(m > 0, q * (log_q - log_m), 0.0)
    
    jsd_contrib = 0.5 * (kl_pm + kl_qm)
    jsd_block = tl.sum(jsd_contrib, 1)
    
    out_ptrs = output + offs_m
    tl.atomic_add(out_ptrs, jsd_block, mask=offs_m < M)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                     W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    
    device = X.device
    
    log_sum_exp1 = torch.empty(M, dtype=torch.float32, device=device)
    log_sum_exp2 = torch.empty(M, dtype=torch.float32, device=device)
    output = torch.zeros(M, dtype=torch.float32, device=device)
    
    def get_config(M, N, K):
        if M <= 128:
            BLOCK_SIZE_M = 32
            BLOCK_SIZE_N = 64
            BLOCK_SIZE_K = 64
            GROUP_SIZE_M = 4
        else:
            BLOCK_SIZE_M = 64
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 64
            GROUP_SIZE_M = 4
        
        num_warps = 4
        if BLOCK_SIZE_N >= 128:
            num_warps = 8
        elif BLOCK_SIZE_N >= 256:
            num_warps = 16
        
        return {
            'BLOCK_SIZE_M': BLOCK_SIZE_M,
            'BLOCK_SIZE_N': BLOCK_SIZE_N,
            'BLOCK_SIZE_K': BLOCK_SIZE_K,
            'GROUP_SIZE_M': GROUP_SIZE_M,
            'num_warps': num_warps
        }
    
    config = get_config(M, N, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), 
    )
    
    # Pass 1: Compute log-sum-exp
    _fused_linear_jsd_kernel_pass1[grid](
        X, W1, W2, B1, B2, M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        log_sum_exp1, log_sum_exp2,
        **config
    )
    
    # Reset output for atomic accumulation
    output.zero_()
    
    # Pass 2: Compute JSD
    _fused_linear_jsd_kernel_pass2[grid](
        X, W1, W2, B1, B2, M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        log_sum_exp1, log_sum_exp2,
        output,
        **config
    )
    
    return output
'''
        return {"code": code}
