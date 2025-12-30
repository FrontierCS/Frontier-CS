import torch
import triton
import triton.language as tl
import math
import os

@triton.jit
def gemm_stats_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    L1_ptr, L2_ptr, Stats_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    stride_stats_m, stride_stats_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        x = tl.load(x_ptrs, mask=offs_k[None, :] < K - k * BLOCK_K, other=0.0)
        w1 = tl.load(w1_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        w2 = tl.load(w2_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        
        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)

        x_ptrs += BLOCK_K * stride_xk
        w1_ptrs += BLOCK_K * stride_w1k
        w2_ptrs += BLOCK_K * stride_w2k

    # Add bias
    b1_ptrs = B1_ptr + offs_n
    b2_ptrs = B2_ptr + offs_n
    b1 = tl.load(b1_ptrs, mask=offs_n < N, other=0.0)
    b2 = tl.load(b2_ptrs, mask=offs_n < N, other=0.0)
    acc1 += b1[None, :]
    acc2 += b2[None, :]

    # Store logits
    l1_ptrs = L1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l2_ptrs = L2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)
    mask_m = offs_m[:, None] < M
    mask_n = offs_n[None, :] < N
    
    tl.store(l1_ptrs, acc1, mask=mask_m & mask_n)
    tl.store(l2_ptrs, acc2, mask=mask_m & mask_n)

    # Compute partial stats
    # Mask out-of-bound values for max/sum calculation
    acc1_masked = tl.where(mask_n, acc1, -float('inf'))
    acc2_masked = tl.where(mask_n, acc2, -float('inf'))
    
    max1 = tl.max(acc1_masked, axis=1)
    max2 = tl.max(acc2_masked, axis=1)

    sum_exp1 = tl.sum(tl.exp(acc1_masked - max1[:, None]), axis=1)
    sum_exp2 = tl.sum(tl.exp(acc2_masked - max2[:, None]), axis=1)

    # Store stats: (M, num_n_tiles, 4)
    # Stride stats_n = 4.
    stats_offset = offs_m * stride_stats_m + pid_n * stride_stats_n
    stats_base = Stats_ptr + stats_offset[:, None]
    mask_m_store = offs_m < M
    
    tl.store(stats_base + 0, max1[:, None], mask=mask_m_store[:, None])
    tl.store(stats_base + 1, sum_exp1[:, None], mask=mask_m_store[:, None])
    tl.store(stats_base + 2, max2[:, None], mask=mask_m_store[:, None])
    tl.store(stats_base + 3, sum_exp2[:, None], mask=mask_m_store[:, None])

@triton.jit
def lse_kernel(
    Stats_ptr, LSE1_ptr, LSE2_ptr,
    M, num_n_tiles,
    stride_stats_m, stride_stats_n,
    BLOCK_M: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    gl_max1 = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    gl_sum1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    gl_max2 = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    gl_sum2 = tl.zeros((BLOCK_M,), dtype=tl.float32)

    stats_base = Stats_ptr + offs_m * stride_stats_m
    
    for i in range(num_n_tiles):
        m1 = tl.load(Stats_ptr + offs_m * stride_stats_m + i * stride_stats_n + 0, mask=mask_m, other=-float('inf'))
        s1 = tl.load(Stats_ptr + offs_m * stride_stats_m + i * stride_stats_n + 1, mask=mask_m, other=0.0)
        m2 = tl.load(Stats_ptr + offs_m * stride_stats_m + i * stride_stats_n + 2, mask=mask_m, other=-float('inf'))
        s2 = tl.load(Stats_ptr + offs_m * stride_stats_m + i * stride_stats_n + 3, mask=mask_m, other=0.0)
        
        new_gl_max1 = tl.maximum(gl_max1, m1)
        gl_sum1 = gl_sum1 * tl.exp(gl_max1 - new_gl_max1) + s1 * tl.exp(m1 - new_gl_max1)
        gl_max1 = new_gl_max1
        
        new_gl_max2 = tl.maximum(gl_max2, m2)
        gl_sum2 = gl_sum2 * tl.exp(gl_max2 - new_gl_max2) + s2 * tl.exp(m2 - new_gl_max2)
        gl_max2 = new_gl_max2

    lse1 = gl_max1 + tl.log(gl_sum1)
    lse2 = gl_max2 + tl.log(gl_sum2)
    
    tl.store(LSE1_ptr + offs_m, lse1, mask=mask_m)
    tl.store(LSE2_ptr + offs_m, lse2, mask=mask_m)

@triton.jit
def jsd_kernel(
    L1_ptr, L2_ptr, LSE1_ptr, LSE2_ptr, Out_ptr,
    M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    lse1 = tl.load(LSE1_ptr + offs_m, mask=mask_m, other=0.0)
    lse2 = tl.load(LSE2_ptr + offs_m, mask=mask_m, other=0.0)
    
    l1_ptrs = L1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l2_ptrs = L2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)
    
    l1 = tl.load(l1_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=0.0)
    l2 = tl.load(l2_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=0.0)
    
    log_p = l1 - lse1[:, None]
    log_q = l2 - lse2[:, None]
    
    # Mask out padding to avoid NaN in calculations
    log_p = tl.where(mask_n[None, :], log_p, -float('inf'))
    log_q = tl.where(mask_n[None, :], log_q, -float('inf'))

    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    # log(P+Q)
    max_log = tl.maximum(log_p, log_q)
    term_log_sum = max_log + tl.log(tl.exp(log_p - max_log) + tl.exp(log_q - max_log))
    
    # JSD term: P ln P + Q ln Q - (P+Q) ln(P+Q)
    # For padded elements, p=0, q=0. 0*inf -> NaN usually.
    # But log_p is -inf. p*log_p = 0 mathematically. 
    # Use where to force 0 for padding.
    
    term = p * log_p + q * log_q - (p + q) * term_log_sum
    term = tl.where(mask_n[None, :], term, 0.0)
    
    acc = tl.sum(term, axis=1)
    tl.atomic_add(Out_ptr + offs_m, 0.5 * acc, mask=mask_m)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_K = 64
    
    # Allocate intermediates
    L1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    L2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    
    num_n_tiles = triton.cdiv(N, BLOCK_N)
    stats = torch.empty((M, num_n_tiles, 4), device=X.device, dtype=torch.float32)
    
    grid_gemm = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    
    gemm_stats_kernel[grid_gemm](
        X, W1, B1, W2, B2,
        L1, L2, stats,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1),
        stats.stride(0), stats.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_SIZE_M=8
    )
    
    LSE1 = torch.empty((M,), device=X.device, dtype=torch.float32)
    LSE2 = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    grid_lse = (triton.cdiv(M, BLOCK_M),)
    lse_kernel[grid_lse](
        stats, LSE1, LSE2,
        M, num_n_tiles,
        stats.stride(0), stats.stride(1),
        BLOCK_M=BLOCK_M
    )
    
    Out = torch.full((M,), math.log(2.0), device=X.device, dtype=torch.float32)
    
    grid_jsd = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    jsd_kernel[grid_jsd](
        L1, L2, LSE1, LSE2, Out,
        M, N,
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": open(os.path.abspath(__file__)).read()}