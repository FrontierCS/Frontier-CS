import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _pass1_lse_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    LOGZ1_ptr, LOGZ2_ptr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mmask = offs_m < M

    # Initialize running max and sum for log-sum-exp for both branches
    neg_big = tl.full([BLOCK_M], -1.0e9, tl.float32)
    m1 = neg_big
    m2 = neg_big
    s1 = tl.zeros([BLOCK_M], dtype=tl.float32)
    s2 = tl.zeros([BLOCK_M], dtype=tl.float32)

    # Loop over N in tiles
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        nmask = offs_n < N

        # Accumulators for logits tiles
        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        # Loop over K dimension
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            kmask = offs_k < K

            # Pointers and loads
            a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
            w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

            a = tl.load(a_ptrs, mask=mmask[:, None] & kmask[None, :], other=0.0).to(tl.float16)
            w1 = tl.load(w1_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)
            w2 = tl.load(w2_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)

            acc1 += tl.dot(a, w1)
            acc2 += tl.dot(a, w2)

        # Add bias
        b1 = tl.load(B1_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        # Mask invalid columns with large negative value to avoid affecting max/sum
        neg_val = -1.0e9
        acc1 = tl.where(nmask[None, :], acc1, neg_val)
        acc2 = tl.where(nmask[None, :], acc2, neg_val)

        # Update running max and sum using stable log-sum-exp accumulation
        tile_max1 = tl.max(acc1, 1)
        tile_max2 = tl.max(acc2, 1)

        new_m1 = tl.maximum(m1, tile_max1)
        new_m2 = tl.maximum(m2, tile_max2)

        # Scale old sums
        s1 = s1 * tl.exp(m1 - new_m1)
        s2 = s2 * tl.exp(m2 - new_m2)

        # Add current tile contributions
        s1 += tl.sum(tl.exp(acc1 - new_m1[:, None]), 1)
        s2 += tl.sum(tl.exp(acc2 - new_m2[:, None]), 1)

        m1 = new_m1
        m2 = new_m2

    # Compute final logZ
    eps = 1e-20
    logz1 = m1 + tl.log(tl.maximum(s1, eps))
    logz2 = m2 + tl.log(tl.maximum(s2, eps))

    tl.store(LOGZ1_ptr + offs_m, logz1, mask=mmask)
    tl.store(LOGZ2_ptr + offs_m, logz2, mask=mmask)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _pass2_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    LOGZ1_ptr, LOGZ2_ptr,
    OUT_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mmask = offs_m < M

    # Load logZ for normalization
    logz1 = tl.load(LOGZ1_ptr + offs_m, mask=mmask, other=-1.0e9)
    logz2 = tl.load(LOGZ2_ptr + offs_m, mask=mmask, other=-1.0e9)

    loss = tl.zeros([BLOCK_M], dtype=tl.float32)
    ln2 = 0.6931471805599453

    # Loop over N in tiles
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        nmask = offs_n < N

        # Compute logits tiles
        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            kmask = offs_k < K

            a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
            w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

            a = tl.load(a_ptrs, mask=mmask[:, None] & kmask[None, :], other=0.0).to(tl.float16)
            w1 = tl.load(w1_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)
            w2 = tl.load(w2_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)

            acc1 += tl.dot(a, w1)
            acc2 += tl.dot(a, w2)

        # Add bias
        b1 = tl.load(B1_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        # Compute logP/logQ and the contributions
        # For masked columns, use a large negative value to avoid NaNs; then mask contribution to zero
        neg_big = -1.0e9
        acc1 = tl.where(nmask[None, :], acc1, neg_big)
        acc2 = tl.where(nmask[None, :], acc2, neg_big)

        logp = acc1 - logz1[:, None]
        logq = acc2 - logz2[:, None]

        m = tl.maximum(logp, logq)
        # logsumexp(logp, logq)
        lse2 = m + tl.log(tl.exp(logp - m) + tl.exp(logq - m))
        logm = lse2 - ln2

        p = tl.exp(logp)
        q = tl.exp(logq)

        contrib = 0.5 * (p * (logp - logm) + q * (logq - logm))
        # Zero out invalid columns
        contrib = tl.where(nmask[None, :], contrib, 0.0)
        loss += tl.sum(contrib, 1)

    tl.store(OUT_ptr + offs_m, loss, mask=mmask)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, "X, W1, W2 must be float16"
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "Biases must be float32"
    assert X.shape[1] == W1.shape[0] == W2.shape[0], "Incompatible K dims"
    assert W1.shape[1] == W2.shape[1] == B1.shape[0] == B2.shape[0], "Incompatible N dims"

    M, K = X.shape
    N = W1.shape[1]

    # Allocate temporary and output
    logz1 = torch.empty((M,), dtype=torch.float32, device=X.device)
    logz2 = torch.empty((M,), dtype=torch.float32, device=X.device)
    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    # Compute strides
    stride_xm = X.stride(0)
    stride_xk = X.stride(1)

    stride_w1k = W1.stride(0)
    stride_w1n = W1.stride(1)
    stride_w2k = W2.stride(0)
    stride_w2n = W2.stride(1)

    # Launch pass1
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    _pass1_lse_kernel[grid](
        X, W1, B1, W2, B2,
        M, N, K,
        stride_xm, stride_xk,
        stride_w1k, stride_w1n,
        stride_w2k, stride_w2n,
        logz1, logz2,
    )

    # Launch pass2
    _pass2_jsd_kernel[grid](
        X, W1, B1, W2, B2,
        logz1, logz2,
        out,
        M, N, K,
        stride_xm, stride_xk,
        stride_w1k, stride_w1n,
        stride_w2k, stride_w2n,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _pass1_lse_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    LOGZ1_ptr, LOGZ2_ptr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mmask = offs_m < M

    neg_big = tl.full([BLOCK_M], -1.0e9, tl.float32)
    m1 = neg_big
    m2 = neg_big
    s1 = tl.zeros([BLOCK_M], dtype=tl.float32)
    s2 = tl.zeros([BLOCK_M], dtype=tl.float32)

    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        nmask = offs_n < N

        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            kmask = offs_k < K

            a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
            w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

            a = tl.load(a_ptrs, mask=mmask[:, None] & kmask[None, :], other=0.0).to(tl.float16)
            w1 = tl.load(w1_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)
            w2 = tl.load(w2_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)

            acc1 += tl.dot(a, w1)
            acc2 += tl.dot(a, w2)

        b1 = tl.load(B1_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        neg_val = -1.0e9
        acc1 = tl.where(nmask[None, :], acc1, neg_val)
        acc2 = tl.where(nmask[None, :], acc2, neg_val)

        tile_max1 = tl.max(acc1, 1)
        tile_max2 = tl.max(acc2, 1)

        new_m1 = tl.maximum(m1, tile_max1)
        new_m2 = tl.maximum(m2, tile_max2)

        s1 = s1 * tl.exp(m1 - new_m1)
        s2 = s2 * tl.exp(m2 - new_m2)

        s1 += tl.sum(tl.exp(acc1 - new_m1[:, None]), 1)
        s2 += tl.sum(tl.exp(acc2 - new_m2[:, None]), 1)

        m1 = new_m1
        m2 = new_m2

    eps = 1e-20
    logz1 = m1 + tl.log(tl.maximum(s1, eps))
    logz2 = m2 + tl.log(tl.maximum(s2, eps))

    tl.store(LOGZ1_ptr + offs_m, logz1, mask=mmask)
    tl.store(LOGZ2_ptr + offs_m, logz2, mask=mmask)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 8, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _pass2_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    LOGZ1_ptr, LOGZ2_ptr,
    OUT_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mmask = offs_m < M

    logz1 = tl.load(LOGZ1_ptr + offs_m, mask=mmask, other=-1.0e9)
    logz2 = tl.load(LOGZ2_ptr + offs_m, mask=mmask, other=-1.0e9)

    loss = tl.zeros([BLOCK_M], dtype=tl.float32)
    ln2 = 0.6931471805599453

    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        nmask = offs_n < N

        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            kmask = offs_k < K

            a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
            w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

            a = tl.load(a_ptrs, mask=mmask[:, None] & kmask[None, :], other=0.0).to(tl.float16)
            w1 = tl.load(w1_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)
            w2 = tl.load(w2_ptrs, mask=kmask[:, None] & nmask[None, :], other=0.0).to(tl.float16)

            acc1 += tl.dot(a, w1)
            acc2 += tl.dot(a, w2)

        b1 = tl.load(B1_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + offs_n, mask=nmask, other=0.0).to(tl.float32)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        neg_big = -1.0e9
        acc1 = tl.where(nmask[None, :], acc1, neg_big)
        acc2 = tl.where(nmask[None, :], acc2, neg_big)

        logp = acc1 - logz1[:, None]
        logq = acc2 - logz2[:, None]

        m = tl.maximum(logp, logq)
        lse2 = m + tl.log(tl.exp(logp - m) + tl.exp(logq - m))
        logm = lse2 - ln2

        p = tl.exp(logp)
        q = tl.exp(logq)

        contrib = 0.5 * (p * (logp - logm) + q * (logq - logm))
        contrib = tl.where(nmask[None, :], contrib, 0.0)
        loss += tl.sum(contrib, 1)

    tl.store(OUT_ptr + offs_m, loss, mask=mmask)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, "X, W1, W2 must be float16"
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "Biases must be float32"
    assert X.shape[1] == W1.shape[0] == W2.shape[0], "Incompatible K dims"
    assert W1.shape[1] == W2.shape[1] == B1.shape[0] == B2.shape[0], "Incompatible N dims"

    M, K = X.shape
    N = W1.shape[1]

    logz1 = torch.empty((M,), dtype=torch.float32, device=X.device)
    logz2 = torch.empty((M,), dtype=torch.float32, device=X.device)
    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_w1k = W1.stride(0)
    stride_w1n = W1.stride(1)
    stride_w2k = W2.stride(0)
    stride_w2n = W2.stride(1)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

    _pass1_lse_kernel[grid](
        X, W1, B1, W2, B2,
        M, N, K,
        stride_xm, stride_xk,
        stride_w1k, stride_w1n,
        stride_w2k, stride_w2n,
        logz1, logz2,
    )

    _pass2_jsd_kernel[grid](
        X, W1, B1, W2, B2,
        logz1, logz2,
        out,
        M, N, K,
        stride_xm, stride_xk,
        stride_w1k, stride_w1n,
        stride_w2k, stride_w2n,
    )

    return out
'''
        return {"code": code}
