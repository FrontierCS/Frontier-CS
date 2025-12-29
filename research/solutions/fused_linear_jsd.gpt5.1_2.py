import os
import sys
import inspect
import math

import torch
import triton
import triton.language as tl


@triton.jit
def _linear_lse_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    LSE1_ptr, LSE2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1, stride_b2,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    NEG_LARGE = -1e9

    # Base pointer for this row of X
    x_row_ptr = X_ptr + pid_m * stride_xm

    max1 = tl.full((), -float("inf"), dtype=tl.float32)
    max2 = tl.full((), -float("inf"), dtype=tl.float32)
    sumexp1 = tl.zeros((), dtype=tl.float32)
    sumexp2 = tl.zeros((), dtype=tl.float32)

    offs_n_init = tl.arange(0, BLOCK_N)
    offs_k_init = tl.arange(0, BLOCK_K)

    start_n = 0
    while start_n < N:
        offs_n = start_n + offs_n_init
        mask_n = offs_n < N

        acc1 = tl.zeros([BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_N], dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + offs_k_init
            mask_k = offs_k < K

            x = tl.load(
                x_row_ptr + offs_k * stride_xk,
                mask=mask_k,
                other=0.0,
            )
            x = x.to(tl.float32)

            w1 = tl.load(
                W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )
            w2 = tl.load(
                W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )

            w1 = w1.to(tl.float32)
            w2 = w2.to(tl.float32)

            acc1 += tl.sum(w1 * x[:, None], axis=0)
            acc2 += tl.sum(w2 * x[:, None], axis=0)

            k += BLOCK_K

        b1 = tl.load(
            B1_ptr + offs_n * stride_b1,
            mask=mask_n,
            other=0.0,
        )
        b2 = tl.load(
            B2_ptr + offs_n * stride_b2,
            mask=mask_n,
            other=0.0,
        )

        logits1 = acc1 + b1
        logits2 = acc2 + b2

        logits1 = tl.where(mask_n, logits1, NEG_LARGE)
        logits2 = tl.where(mask_n, logits2, NEG_LARGE)

        tile_max1 = tl.max(logits1, axis=0)
        tile_max2 = tl.max(logits2, axis=0)

        new_max1 = tl.maximum(max1, tile_max1)
        new_max2 = tl.maximum(max2, tile_max2)

        exp1 = tl.exp(logits1 - new_max1)
        exp2 = tl.exp(logits2 - new_max2)

        sumexp1 = sumexp1 * tl.exp(max1 - new_max1) + tl.sum(exp1, axis=0)
        sumexp2 = sumexp2 * tl.exp(max2 - new_max2) + tl.sum(exp2, axis=0)

        max1 = new_max1
        max2 = new_max2

        start_n += BLOCK_N

    lse1 = tl.log(sumexp1) + max1
    lse2 = tl.log(sumexp2) + max2

    tl.store(LSE1_ptr + pid_m, lse1)
    tl.store(LSE2_ptr + pid_m, lse2)


@triton.jit
def _jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    LSE1_ptr, LSE2_ptr,
    OUT_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1, stride_b2,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    NEG_LARGE = -1e9
    LOG2 = 0.6931471805599453

    x_row_ptr = X_ptr + pid_m * stride_xm

    lse1 = tl.load(LSE1_ptr + pid_m)
    lse2 = tl.load(LSE2_ptr + pid_m)

    jsd_val = tl.zeros((), dtype=tl.float32)

    offs_n_init = tl.arange(0, BLOCK_N)
    offs_k_init = tl.arange(0, BLOCK_K)

    start_n = 0
    while start_n < N:
        offs_n = start_n + offs_n_init
        mask_n = offs_n < N

        acc1 = tl.zeros([BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_N], dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + offs_k_init
            mask_k = offs_k < K

            x = tl.load(
                x_row_ptr + offs_k * stride_xk,
                mask=mask_k,
                other=0.0,
            )
            x = x.to(tl.float32)

            w1 = tl.load(
                W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )
            w2 = tl.load(
                W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )

            w1 = w1.to(tl.float32)
            w2 = w2.to(tl.float32)

            acc1 += tl.sum(w1 * x[:, None], axis=0)
            acc2 += tl.sum(w2 * x[:, None], axis=0)

            k += BLOCK_K

        b1 = tl.load(
            B1_ptr + offs_n * stride_b1,
            mask=mask_n,
            other=0.0,
        )
        b2 = tl.load(
            B2_ptr + offs_n * stride_b2,
            mask=mask_n,
            other=0.0,
        )

        logits1 = acc1 + b1
        logits2 = acc2 + b2

        logits1 = tl.where(mask_n, logits1, NEG_LARGE)
        logits2 = tl.where(mask_n, logits2, NEG_LARGE)

        a = logits1 - lse1  # log P
        b = logits2 - lse2  # log Q

        maxab = tl.maximum(a, b)
        exp_a = tl.exp(a)
        exp_b = tl.exp(b)

        tmp1 = tl.exp(a - maxab)
        tmp2 = tl.exp(b - maxab)
        logm = maxab + tl.log(tmp1 + tmp2) - LOG2  # log M

        contrib = exp_a * (a - logm) + exp_b * (b - logm)
        jsd_val += 0.5 * tl.sum(contrib, axis=0)

        start_n += BLOCK_N

    tl.store(OUT_ptr + pid_m, jsd_val)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K1 == K and K2 == K and N2 == N
    assert B1.shape[0] == N and B2.shape[0] == N

    X_c = X
    W1_c = W1
    W2_c = W2
    B1_c = B1
    B2_c = B2

    lse1 = torch.empty((M,), device=X_c.device, dtype=torch.float32)
    lse2 = torch.empty((M,), device=X_c.device, dtype=torch.float32)
    out = torch.empty((M,), device=X_c.device, dtype=torch.float32)

    BLOCK_N = 128
    BLOCK_K = 32

    grid = (M,)

    _linear_lse_kernel[grid](
        X_c, W1_c, B1_c, W2_c, B2_c,
        lse1, lse2,
        M, N, K,
        X_c.stride(0), X_c.stride(1),
        W1_c.stride(0), W1_c.stride(1),
        W2_c.stride(0), W2_c.stride(1),
        B1_c.stride(0), B2_c.stride(0),
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    _jsd_kernel[grid](
        X_c, W1_c, B1_c, W2_c, B2_c,
        lse1, lse2,
        out,
        M, N, K,
        X_c.stride(0), X_c.stride(1),
        W1_c.stride(0), W1_c.stride(1),
        W2_c.stride(0), W2_c.stride(1),
        B1_c.stride(0), B2_c.stride(0),
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except NameError:
            pass
        src = inspect.getsource(sys.modules[__name__])
        return {"code": src}