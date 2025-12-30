import os
import sys
import math
import inspect
from collections import OrderedDict

import torch

try:
    import triton
    import triton.language as tl
    _HAS_TRITON = True
except Exception:
    triton = None
    tl = None
    _HAS_TRITON = False


_WCAT_CACHE = OrderedDict()
_WORKSPACE_CACHE = OrderedDict()
_MAX_CACHE_ITEMS = 8


def _cache_put(cache: OrderedDict, key, value, max_items: int = _MAX_CACHE_ITEMS):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > max_items:
        cache.popitem(last=False)


def _get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
    # Ensure caching is safe w.r.t. in-place mutations by using _version.
    key = (
        int(W1.data_ptr()),
        int(W2.data_ptr()),
        int(getattr(W1, "_version", 0)),
        int(getattr(W2, "_version", 0)),
        tuple(W1.shape),
        tuple(W2.shape),
        str(W1.device),
        str(W1.dtype),
    )
    Wcat = _WCAT_CACHE.get(key, None)
    if Wcat is not None and Wcat.is_cuda:
        _WCAT_CACHE.move_to_end(key)
        return Wcat

    W1c = W1 if W1.is_contiguous() else W1.contiguous()
    W2c = W2 if W2.is_contiguous() else W2.contiguous()
    Wcat = torch.cat((W1c, W2c), dim=1).contiguous()
    _cache_put(_WCAT_CACHE, key, Wcat)
    return Wcat


def _get_workspace(device: torch.device, M: int, twoN: int, dtype: torch.dtype) -> torch.Tensor:
    key = (str(device), int(M), int(twoN), str(dtype))
    ws = _WORKSPACE_CACHE.get(key, None)
    if ws is not None and ws.is_cuda and ws.numel() == M * twoN and ws.dtype == dtype:
        _WORKSPACE_CACHE.move_to_end(key)
        return ws
    ws = torch.empty((M, twoN), device=device, dtype=dtype)
    _cache_put(_WORKSPACE_CACHE, key, ws)
    return ws


if _HAS_TRITON:
    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=2),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=2),
        ],
        key=["N"],
    )
    @triton.jit
    def _jsd_from_logitscat_kernel(
        LOGITS_CAT,  # [M, 2N] fp16
        B1,          # [N] fp32
        B2,          # [N] fp32
        OUT,         # [M] fp32
        M: tl.constexpr,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        row = pid_m
        row_mask = row < M

        # Base pointers for this row
        row_base = LOGITS_CAT + row * (2 * N)

        neg_inf = tl.full((), -float("inf"), tl.float32)
        max1 = neg_inf
        max2 = neg_inf

        offs = tl.arange(0, BLOCK_N)
        # Pass 1: max
        for n0 in tl.static_range(0, N, BLOCK_N):
            cols = n0 + offs
            mask = cols < N

            l1 = tl.load(row_base + cols, mask=mask & row_mask, other=-float("inf")).to(tl.float32)
            l2 = tl.load(row_base + (cols + N), mask=mask & row_mask, other=-float("inf")).to(tl.float32)
            b1 = tl.load(B1 + cols, mask=mask, other=0.0).to(tl.float32)
            b2 = tl.load(B2 + cols, mask=mask, other=0.0).to(tl.float32)

            l1 = l1 + b1
            l2 = l2 + b2

            max1 = tl.maximum(max1, tl.max(l1, axis=0))
            max2 = tl.maximum(max2, tl.max(l2, axis=0))

        # Pass 2: sum exp
        sum1 = tl.zeros((), dtype=tl.float32)
        sum2 = tl.zeros((), dtype=tl.float32)

        for n0 in tl.static_range(0, N, BLOCK_N):
            cols = n0 + offs
            mask = cols < N

            l1 = tl.load(row_base + cols, mask=mask & row_mask, other=-float("inf")).to(tl.float32)
            l2 = tl.load(row_base + (cols + N), mask=mask & row_mask, other=-float("inf")).to(tl.float32)
            b1 = tl.load(B1 + cols, mask=mask, other=0.0).to(tl.float32)
            b2 = tl.load(B2 + cols, mask=mask, other=0.0).to(tl.float32)

            l1 = l1 + b1
            l2 = l2 + b2

            e1 = tl.exp(l1 - max1)
            e2 = tl.exp(l2 - max2)
            e1 = tl.where(mask & row_mask, e1, 0.0)
            e2 = tl.where(mask & row_mask, e2, 0.0)
            sum1 += tl.sum(e1, axis=0)
            sum2 += tl.sum(e2, axis=0)

        lse1 = max1 + tl.log(sum1)
        lse2 = max2 + tl.log(sum2)

        # Pass 3: JSD
        acc = tl.zeros((), dtype=tl.float32)
        log2 = tl.full((), 0.6931471805599453, tl.float32)
        eps = tl.full((), 1e-20, tl.float32)

        for n0 in tl.static_range(0, N, BLOCK_N):
            cols = n0 + offs
            mask = cols < N

            l1 = tl.load(row_base + cols, mask=mask & row_mask, other=-float("inf")).to(tl.float32)
            l2 = tl.load(row_base + (cols + N), mask=mask & row_mask, other=-float("inf")).to(tl.float32)
            b1 = tl.load(B1 + cols, mask=mask, other=0.0).to(tl.float32)
            b2 = tl.load(B2 + cols, mask=mask, other=0.0).to(tl.float32)

            l1 = l1 + b1
            l2 = l2 + b2

            log_p = l1 - lse1
            log_q = l2 - lse2
            p = tl.exp(log_p)
            q = tl.exp(log_q)

            pq = p + q
            log_m = tl.log(pq + eps) - log2

            term = 0.5 * (p * (log_p - log_m) + q * (log_q - log_m))
            term = tl.where(mask & row_mask, term, 0.0)
            acc += tl.sum(term, axis=0)

        tl.store(OUT + row, acc, mask=row_mask)


def fused_linear_jsd(
    X: torch.Tensor,
    W1: torch.Tensor,
    B1: torch.Tensor,
    W2: torch.Tensor,
    B2: torch.Tensor,
) -> torch.Tensor:
    if (not _HAS_TRITON) or (not X.is_cuda):
        logits1 = X @ W1
        logits2 = X @ W2
        logits1 = logits1.to(torch.float32) + B1
        logits2 = logits2.to(torch.float32) + B2
        P = torch.softmax(logits1, dim=-1)
        Q = torch.softmax(logits2, dim=-1)
        Mdist = 0.5 * (P + Q)
        jsd = 0.5 * (torch.sum(P * (torch.log(P + 1e-20) - torch.log(Mdist + 1e-20)), dim=-1) +
                     torch.sum(Q * (torch.log(Q + 1e-20) - torch.log(Mdist + 1e-20)), dim=-1))
        return jsd.to(torch.float32)

    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    assert X.is_contiguous() or True  # we will make contiguous if needed

    M, K = X.shape
    K1, N = W1.shape
    assert K1 == K and W2.shape == (K, N)
    assert B1.shape == (N,) and B2.shape == (N,)

    Xc = X if X.is_contiguous() else X.contiguous()
    Wcat = _get_wcat(W1, W2)  # [K, 2N]
    twoN = 2 * N

    logits_cat = _get_workspace(Xc.device, M, twoN, torch.float16)
    torch.mm(Xc, Wcat, out=logits_cat)

    out = torch.empty((M,), device=X.device, dtype=torch.float32)
    grid = (M,)
    _jsd_from_logitscat_kernel[grid](
        logits_cat,
        B1,
        B2,
        out,
        M=M,
        N=N,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            code = inspect.getsource(sys.modules[__name__])
            return {"code": code}
        except Exception:
            return {"program_path": os.path.abspath(__file__)}