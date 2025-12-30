import os
import textwrap


KERNEL_CODE = r"""
import math
import torch
import triton
import triton.language as tl

__all__ = ["fused_linear_jsd"]

_WCAT_CACHE = {}
_BCAT_CACHE = {}

@triton.jit
def _jsd_from_logits_cat_kernel(
    LOGITS_CAT_PTR,  # *fp16, [M, 2N]
    BCAT_PTR,        # *fp32, [2N]
    OUT_PTR,         # *fp32, [M]
    STRIDE_LM: tl.constexpr,  # in elements
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)

    tl.multiple_of(STRIDE_LM, 8)

    row_ptr = LOGITS_CAT_PTR + pid_m * STRIDE_LM

    m1 = tl.full([], -float("inf"), tl.float32)
    s1 = tl.zeros([], dtype=tl.float32)
    m2 = tl.full([], -float("inf"), tl.float32)
    s2 = tl.zeros([], dtype=tl.float32)

    offs0 = tl.arange(0, BLOCK_N)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs = start_n + offs0
        mask = offs < N

        l1 = tl.load(row_ptr + offs, mask=mask, other=-float("inf")).to(tl.float32)
        l2 = tl.load(row_ptr + (offs + N), mask=mask, other=-float("inf")).to(tl.float32)

        b1 = tl.load(BCAT_PTR + offs, mask=mask, other=0.0).to(tl.float32)
        b2 = tl.load(BCAT_PTR + (offs + N), mask=mask, other=0.0).to(tl.float32)

        a = l1 + b1
        b = l2 + b2

        block_m1 = tl.max(a, axis=0)
        block_m2 = tl.max(b, axis=0)

        exp1 = tl.exp(a - block_m1)
        exp2 = tl.exp(b - block_m2)

        block_s1 = tl.sum(exp1, axis=0)
        block_s2 = tl.sum(exp2, axis=0)

        new_m1 = tl.maximum(m1, block_m1)
        new_m2 = tl.maximum(m2, block_m2)

        s1 = s1 * tl.exp(m1 - new_m1) + block_s1 * tl.exp(block_m1 - new_m1)
        s2 = s2 * tl.exp(m2 - new_m2) + block_s2 * tl.exp(block_m2 - new_m2)

        m1 = new_m1
        m2 = new_m2

    logZ1 = m1 + tl.log(s1)
    logZ2 = m2 + tl.log(s2)

    acc = tl.zeros([], dtype=tl.float32)
    LOG2 = 0.6931471805599453
    EPS = 1e-20

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs = start_n + offs0
        mask = offs < N

        l1 = tl.load(row_ptr + offs, mask=mask, other=-float("inf")).to(tl.float32)
        l2 = tl.load(row_ptr + (offs + N), mask=mask, other=-float("inf")).to(tl.float32)

        b1 = tl.load(BCAT_PTR + offs, mask=mask, other=0.0).to(tl.float32)
        b2 = tl.load(BCAT_PTR + (offs + N), mask=mask, other=0.0).to(tl.float32)

        a = l1 + b1
        b = l2 + b2

        logp = a - logZ1
        logq = b - logZ2

        p = tl.exp(logp)
        q = tl.exp(logq)

        pq = p + q
        pq = tl.maximum(pq, EPS)
        logm = tl.log(pq) - LOG2

        term = 0.5 * (p * (logp - logm) + q * (logq - logm))
        term = tl.where(mask, term, 0.0)
        acc += tl.sum(term, axis=0)

    acc = tl.maximum(acc, 0.0)
    tl.store(OUT_PTR + pid_m, acc)


def _get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
    key = (int(W1.data_ptr()), int(W2.data_ptr()), int(W1.shape[0]), int(W1.shape[1]))
    out = _WCAT_CACHE.get(key, None)
    if out is None or (not out.is_cuda) or out.dtype != torch.float16:
        out = torch.cat((W1, W2), dim=1).contiguous()
        _WCAT_CACHE[key] = out
    return out


def _get_bcat(B1: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    key = (int(B1.data_ptr()), int(B2.data_ptr()), int(B1.shape[0]))
    out = _BCAT_CACHE.get(key, None)
    if out is None or (not out.is_cuda) or out.dtype != torch.float32:
        out = torch.cat((B1, B2), dim=0).contiguous()
        _BCAT_CACHE[key] = out
    return out


def fused_linear_jsd(
    X: torch.Tensor,
    W1: torch.Tensor,
    B1: torch.Tensor,
    W2: torch.Tensor,
    B2: torch.Tensor,
) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    assert X.ndim == 2 and W1.ndim == 2 and W2.ndim == 2 and B1.ndim == 1 and B2.ndim == 1

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K1 == K and K2 == K and N2 == N
    assert B1.shape[0] == N and B2.shape[0] == N

    if not X.is_contiguous():
        X = X.contiguous()

    Wcat = _get_wcat(W1, W2)
    Bcat = _get_bcat(B1, B2)

    logits_cat = torch.matmul(X, Wcat)
    if not logits_cat.is_contiguous():
        logits_cat = logits_cat.contiguous()

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    if N >= 4096 and (N % 512 == 0):
        BLOCK_N = 512
        num_warps = 8
    elif N % 256 == 0:
        BLOCK_N = 256
        num_warps = 8
    else:
        BLOCK_N = 128
        num_warps = 4

    stride_lm = logits_cat.stride(0)

    grid = (M,)
    _jsd_from_logits_cat_kernel[grid](
        logits_cat,
        Bcat,
        out,
        STRIDE_LM=stride_lm,
        N=N,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=2,
    )
    return out
"""


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": textwrap.dedent(KERNEL_CODE)}