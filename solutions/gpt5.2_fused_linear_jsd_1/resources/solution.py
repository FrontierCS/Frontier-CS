import os
import math
from typing import Dict, Tuple, Optional

import torch
import triton
import triton.language as tl


@triton.jit
def _mm2_kernel(
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    L1_ptr,
    L2_ptr,
    M,
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_w2k,
    stride_w2n,
    stride_l1m,
    stride_l1n,
    stride_l2m,
    stride_l2n,
    N: tl.constexpr,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    tl.multiple_of(stride_xk, 1)
    tl.multiple_of(stride_w1n, 1)
    tl.multiple_of(stride_w2n, 1)
    tl.multiple_of(stride_l1n, 1)
    tl.multiple_of(stride_l2n, 1)

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    n_mask = offs_n < N
    m_mask = offs_m < M

    for k0 in tl.static_range(0, K, BLOCK_K):
        k = k0 + offs_k
        k_mask = k < K

        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + k[None, :] * stride_xk)
        a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)

        w1_ptrs = W1_ptr + (k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptrs = W2_ptr + (k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

        w1 = tl.load(w1_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
        w2 = tl.load(w2_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

        acc1 += tl.dot(a, w1)
        acc2 += tl.dot(a, w2)

    b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
    b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)

    acc1 = acc1 + b1[None, :]
    acc2 = acc2 + b2[None, :]

    l1_ptrs = L1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l2_ptrs = L2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)

    out_mask = m_mask[:, None] & n_mask[None, :]
    tl.store(l1_ptrs, acc1, mask=out_mask)
    tl.store(l2_ptrs, acc2, mask=out_mask)


@triton.jit
def _jsd_from_logits_kernel(
    L1_ptr,
    L2_ptr,
    Out_ptr,
    stride_lm,
    stride_ln,
    M,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    offs = tl.arange(0, BLOCK_N)

    max1 = tl.full((), -float("inf"), tl.float32)
    max2 = tl.full((), -float("inf"), tl.float32)

    base = row * stride_lm

    for start in tl.static_range(0, N, BLOCK_N):
        idx = start + offs
        mask = idx < N

        l1 = tl.load(L1_ptr + base + idx * stride_ln, mask=mask, other=-float("inf"))
        l2 = tl.load(L2_ptr + base + idx * stride_ln, mask=mask, other=-float("inf"))

        max1 = tl.maximum(max1, tl.max(l1, axis=0))
        max2 = tl.maximum(max2, tl.max(l2, axis=0))

    sum1 = tl.zeros((), tl.float32)
    sum2 = tl.zeros((), tl.float32)

    for start in tl.static_range(0, N, BLOCK_N):
        idx = start + offs
        mask = idx < N

        l1 = tl.load(L1_ptr + base + idx * stride_ln, mask=mask, other=-float("inf"))
        l2 = tl.load(L2_ptr + base + idx * stride_ln, mask=mask, other=-float("inf"))

        sum1 += tl.sum(tl.exp(l1 - max1), axis=0)
        sum2 += tl.sum(tl.exp(l2 - max2), axis=0)

    logz1 = max1 + tl.log(sum1)
    logz2 = max2 + tl.log(sum2)

    jsd = tl.zeros((), tl.float32)
    eps = 1.0e-20

    for start in tl.static_range(0, N, BLOCK_N):
        idx = start + offs
        mask = idx < N

        l1 = tl.load(L1_ptr + base + idx * stride_ln, mask=mask, other=-1.0e20)
        l2 = tl.load(L2_ptr + base + idx * stride_ln, mask=mask, other=-1.0e20)

        logp = l1 - logz1
        logq = l2 - logz2

        p = tl.exp(logp)
        q = tl.exp(logq)

        m = 0.5 * (p + q)
        m = tl.maximum(m, eps)
        logm = tl.log(m)

        jsd += tl.sum(0.5 * (p * (logp - logm) + q * (logq - logm)), axis=0)

    tl.store(Out_ptr + row, jsd)


_logits_cache: Dict[Tuple[int, int, int], Tuple[torch.Tensor, torch.Tensor]] = {}


def _get_logits_buffers(device: torch.device, M: int, N: int) -> Tuple[torch.Tensor, torch.Tensor]:
    key = (device.index if device.type == "cuda" else -1, M, N)
    bufs = _logits_cache.get(key, None)
    if bufs is not None:
        l1, l2 = bufs
        if l1.is_cuda and l2.is_cuda and l1.shape == (M, N) and l2.shape == (M, N) and l1.dtype == torch.float32 and l2.dtype == torch.float32:
            return l1, l2
    l1 = torch.empty((M, N), device=device, dtype=torch.float32)
    l2 = torch.empty((M, N), device=device, dtype=torch.float32)
    _logits_cache[key] = (l1, l2)
    return l1, l2


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if X.dtype != torch.float16 or W1.dtype != torch.float16 or W2.dtype != torch.float16:
        raise ValueError("X, W1, W2 must be torch.float16.")
    if B1.dtype != torch.float32 or B2.dtype != torch.float32:
        B1 = B1.float()
        B2 = B2.float()

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    if K1 != K or K2 != K or N2 != N:
        raise ValueError("Shape mismatch.")

    device = X.device
    L1, L2 = _get_logits_buffers(device, M, N)
    out = torch.empty((M,), device=device, dtype=torch.float32)

    BLOCK_M = 32
    BLOCK_N_MM = 64
    BLOCK_K = 64

    grid_mm = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N_MM))
    _mm2_kernel[grid_mm](
        X,
        W1,
        B1,
        W2,
        B2,
        L1,
        L2,
        M,
        X.stride(0),
        X.stride(1),
        W1.stride(0),
        W1.stride(1),
        W2.stride(0),
        W2.stride(1),
        L1.stride(0),
        L1.stride(1),
        L2.stride(0),
        L2.stride(1),
        N=N,
        K=K,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N_MM,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=4,
    )

    BLOCK_N_JSD = 512
    _jsd_from_logits_kernel[(M,)](
        L1,
        L2,
        out,
        L1.stride(0),
        L1.stride(1),
        M,
        N=N,
        BLOCK_N=BLOCK_N_JSD,
        num_warps=8,
        num_stages=2,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
