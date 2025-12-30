import math
import os
import textwrap

import torch
import triton
import triton.language as tl


KERNEL_CODE = textwrap.dedent(r"""
import math
import torch
import triton
import triton.language as tl

_LOG2 = 0.6931471805599453

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Out_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr,
):
    pid_m = tl.program_id(0)
    rows = pid_m * BM + tl.arange(0, BM)
    row_mask = rows < M

    m1 = tl.full((BM,), -float("inf"), tl.float32)
    s1 = tl.zeros((BM,), tl.float32)
    m2 = tl.full((BM,), -float("inf"), tl.float32)
    s2 = tl.zeros((BM,), tl.float32)

    # Pass 1: compute log-sum-exp for both branches (streaming)
    for n0 in range(0, N, BN):
        cols = n0 + tl.arange(0, BN)
        col_mask = cols < N

        acc1 = tl.zeros((BM, BN), tl.float32)
        acc2 = tl.zeros((BM, BN), tl.float32)

        for k0 in range(0, K, BK):
            ks = k0 + tl.arange(0, BK)
            k_mask = ks < K

            x = tl.load(
                X_ptr + rows[:, None] * stride_xm + ks[None, :] * stride_xk,
                mask=row_mask[:, None] & k_mask[None, :],
                other=0.0,
            ).to(tl.float16)

            w1 = tl.load(
                W1_ptr + ks[:, None] * stride_wk + cols[None, :] * stride_wn,
                mask=k_mask[:, None] & col_mask[None, :],
                other=0.0,
                cache_modifier=".ca",
            ).to(tl.float16)
            w2 = tl.load(
                W2_ptr + ks[:, None] * stride_wk + cols[None, :] * stride_wn,
                mask=k_mask[:, None] & col_mask[None, :],
                other=0.0,
                cache_modifier=".ca",
            ).to(tl.float16)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        b1 = tl.load(B1_ptr + cols, mask=col_mask, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + cols, mask=col_mask, other=0.0).to(tl.float32)

        logits1 = acc1 + b1[None, :]
        logits2 = acc2 + b2[None, :]

        logits1 = tl.where(col_mask[None, :], logits1, -float("inf"))
        logits2 = tl.where(col_mask[None, :], logits2, -float("inf"))

        tmax1 = tl.max(logits1, axis=1)
        new_m1 = tl.maximum(m1, tmax1)
        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(logits1 - new_m1[:, None]), axis=1)
        m1 = new_m1

        tmax2 = tl.max(logits2, axis=1)
        new_m2 = tl.maximum(m2, tmax2)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(logits2 - new_m2[:, None]), axis=1)
        m2 = new_m2

    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)

    # Pass 2: recompute logits and accumulate JSD
    jsd = tl.zeros((BM,), tl.float32)
    for n0 in range(0, N, BN):
        cols = n0 + tl.arange(0, BN)
        col_mask = cols < N
        valid = col_mask[None, :]

        acc1 = tl.zeros((BM, BN), tl.float32)
        acc2 = tl.zeros((BM, BN), tl.float32)

        for k0 in range(0, K, BK):
            ks = k0 + tl.arange(0, BK)
            k_mask = ks < K

            x = tl.load(
                X_ptr + rows[:, None] * stride_xm + ks[None, :] * stride_xk,
                mask=row_mask[:, None] & k_mask[None, :],
                other=0.0,
            ).to(tl.float16)

            w1 = tl.load(
                W1_ptr + ks[:, None] * stride_wk + cols[None, :] * stride_wn,
                mask=k_mask[:, None] & col_mask[None, :],
                other=0.0,
                cache_modifier=".ca",
            ).to(tl.float16)
            w2 = tl.load(
                W2_ptr + ks[:, None] * stride_wk + cols[None, :] * stride_wn,
                mask=k_mask[:, None] & col_mask[None, :],
                other=0.0,
                cache_modifier=".ca",
            ).to(tl.float16)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        b1 = tl.load(B1_ptr + cols, mask=col_mask, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + cols, mask=col_mask, other=0.0).to(tl.float32)
        logits1 = acc1 + b1[None, :]
        logits2 = acc2 + b2[None, :]

        logp = (logits1 - lse1[:, None]).to(tl.float32)
        logq = (logits2 - lse2[:, None]).to(tl.float32)

        # Avoid NaNs on masked lanes
        logp = tl.where(valid, logp, 0.0)
        logq = tl.where(valid, logq, 0.0)

        p = tl.where(valid, tl.exp(logp), 0.0)
        q = tl.where(valid, tl.exp(logq), 0.0)

        max_l = tl.maximum(logp, logq)
        logm = max_l + tl.log(tl.exp(logp - max_l) + tl.exp(logq - max_l)) - _LOG2

        term = p * (logp - logm) + q * (logq - logm)
        jsd += 0.5 * tl.sum(term, axis=1)

    tl.store(Out_ptr + rows, jsd, mask=row_mask)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not X.is_cuda:
        logits1 = X.float().matmul(W1.float()) + B1
        logits2 = X.float().matmul(W2.float()) + B2
        p = torch.softmax(logits1, dim=-1)
        q = torch.softmax(logits2, dim=-1)
        m = 0.5 * (p + q)
        jsd = 0.5 * (torch.sum(p * (torch.log(p + 1e-20) - torch.log(m + 1e-20)), dim=-1) +
                     torch.sum(q * (torch.log(q + 1e-20) - torch.log(m + 1e-20)), dim=-1))
        return jsd

    X = X.contiguous()
    W1 = W1.contiguous()
    W2 = W2.contiguous()
    B1 = B1.contiguous()
    B2 = B2.contiguous()

    M, K = X.shape
    K2, N = W1.shape
    assert K == K2
    assert W2.shape[0] == K and W2.shape[1] == N
    assert B1.numel() == N and B2.numel() == N

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    BM = 2
    BN = 64
    BK = 64

    grid = (triton.cdiv(M, BM),)
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, out,
        M=M, N=N, K=K,
        stride_xm=X.stride(0), stride_xk=X.stride(1),
        stride_wk=W1.stride(0), stride_wn=W1.stride(1),
        BM=BM, BN=BN, BK=BK,
        num_warps=4,
        num_stages=3,
    )
    return out
""").strip() + "\n"

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}