import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl

_LOG2 = 0.6931471805599453
_EPS = 1.0e-20

_WCAT_CACHE = {}
_WCAT_CACHE_ORDER = []
_WCAT_CACHE_MAX = 4


def _cache_get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
    global _WCAT_CACHE, _WCAT_CACHE_ORDER
    key = (W1.data_ptr(), W2.data_ptr(), W1.shape, W2.shape, W1.stride(), W2.stride(), W1.dtype, W2.dtype, W1.device)
    wcat = _WCAT_CACHE.get(key, None)
    if wcat is not None and wcat.is_cuda and wcat.dtype == torch.float16 and wcat.shape == (W1.shape[0], W1.shape[1] * 2):
        return wcat
    K, N = W1.shape
    wcat = torch.empty((K, 2 * N), device=W1.device, dtype=torch.float16)
    wcat[:, :N].copy_(W1)
    wcat[:, N:].copy_(W2)
    _WCAT_CACHE[key] = wcat
    _WCAT_CACHE_ORDER.append(key)
    if len(_WCAT_CACHE_ORDER) > _WCAT_CACHE_MAX:
        old = _WCAT_CACHE_ORDER.pop(0)
        _WCAT_CACHE.pop(old, None)
    return wcat


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _jsd_from_logits_cat_kernel(
    logits_ptr,  # fp16 [M, 2N]
    b1_ptr,      # fp32 [N]
    b2_ptr,      # fp32 [N]
    out_ptr,     # fp32 [M]
    stride_lm,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    row_off = pid_m * stride_lm
    row_ptr = logits_ptr + row_off

    offs = tl.arange(0, BLOCK_N)

    m1 = tl.full((), -1.0e20, tl.float32)
    s1 = tl.zeros((), tl.float32)
    m2 = tl.full((), -1.0e20, tl.float32)
    s2 = tl.zeros((), tl.float32)

    for n0 in tl.static_range(0, N, BLOCK_N):
        cols = n0 + offs
        mask = cols < N

        l1 = tl.load(row_ptr + cols, mask=mask, other=-1.0e20).to(tl.float32)
        l2 = tl.load(row_ptr + N + cols, mask=mask, other=-1.0e20).to(tl.float32)
        b1 = tl.load(b1_ptr + cols, mask=mask, other=0.0).to(tl.float32)
        b2 = tl.load(b2_ptr + cols, mask=mask, other=0.0).to(tl.float32)

        x1 = l1 + b1
        x2 = l2 + b2

        block_max1 = tl.max(x1, axis=0)
        m1_new = tl.maximum(m1, block_max1)
        s1 = s1 * tl.exp(m1 - m1_new) + tl.sum(tl.exp(x1 - m1_new), axis=0)
        m1 = m1_new

        block_max2 = tl.max(x2, axis=0)
        m2_new = tl.maximum(m2, block_max2)
        s2 = s2 * tl.exp(m2 - m2_new) + tl.sum(tl.exp(x2 - m2_new), axis=0)
        m2 = m2_new

    s1 = tl.maximum(s1, _EPS)
    s2 = tl.maximum(s2, _EPS)
    lse1 = tl.log(s1) + m1
    lse2 = tl.log(s2) + m2

    acc = tl.zeros((), tl.float32)

    for n0 in tl.static_range(0, N, BLOCK_N):
        cols = n0 + offs
        mask = cols < N

        l1 = tl.load(row_ptr + cols, mask=mask, other=-1.0e20).to(tl.float32)
        l2 = tl.load(row_ptr + N + cols, mask=mask, other=-1.0e20).to(tl.float32)
        b1 = tl.load(b1_ptr + cols, mask=mask, other=0.0).to(tl.float32)
        b2 = tl.load(b2_ptr + cols, mask=mask, other=0.0).to(tl.float32)

        x1 = l1 + b1
        x2 = l2 + b2

        logp = x1 - lse1
        logq = x2 - lse2

        p = tl.exp(logp)
        q = tl.exp(logq)

        pq = tl.maximum(p + q, _EPS)
        logm = tl.log(pq) - _LOG2

        term = p * (logp - logm) + q * (logq - logm)
        acc += tl.sum(term, axis=0)

    out = 0.5 * acc
    tl.store(out_ptr + pid_m, out)


@torch.no_grad()
def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
        logits1 = X @ W1
        logits2 = X @ W2
        logits1 = logits1 + B1
        logits2 = logits2 + B2
        p = torch.softmax(logits1.float(), dim=-1)
        q = torch.softmax(logits2.float(), dim=-1)
        m = 0.5 * (p + q)
        jsd = 0.5 * (torch.sum(p * (torch.log(p + 1e-20) - torch.log(m + 1e-20)), dim=-1) +
                     torch.sum(q * (torch.log(q + 1e-20) - torch.log(m + 1e-20)), dim=-1))
        return jsd.float()

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W1.dtype != torch.float16:
        W1 = W1.to(torch.float16)
    if W2.dtype != torch.float16:
        W2 = W2.to(torch.float16)
    if B1.dtype != torch.float32:
        B1 = B1.to(torch.float32)
    if B2.dtype != torch.float32:
        B2 = B2.to(torch.float32)

    X = X.contiguous()
    W1 = W1.contiguous()
    W2 = W2.contiguous()
    B1 = B1.contiguous()
    B2 = B2.contiguous()

    M, K = X.shape
    K1, N = W1.shape
    if K1 != K or W2.shape != (K, N) or B1.numel() != N or B2.numel() != N:
        raise ValueError("Shape mismatch")

    wcat = _cache_get_wcat(W1, W2)
    logits_cat = (X @ wcat).contiguous()  # fp16 [M, 2N]

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = (M,)
    _jsd_from_logits_cat_kernel[grid](
        logits_cat, B1, B2, out,
        stride_lm=logits_cat.stride(0),
        N=N,
    )
    return out
'''
        return {"code": textwrap.dedent(code).lstrip()}
