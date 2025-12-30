import math
import os
from typing import Dict, Optional, Tuple

import torch
import triton
import triton.language as tl


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


def _next_pow2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 16, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_K": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_K": 64}, num_warps=8, num_stages=3),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _partial_stats_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    T_ptr,
    out_max_ptr,
    out_sum_ptr,
    out_tgt_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm: tl.constexpr,
    stride_xk: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_wn: tl.constexpr,
    stride_pm: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_b * BLOCK_N + tl.arange(0, BLOCK_N)

    m_mask = m_offsets < M
    n_mask = n_offsets < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_offsets = tl.arange(0, BLOCK_K)
    for k0 in tl.static_range(0, K, BLOCK_K):
        k = k0 + k_offsets
        k_mask = k < K

        a = tl.load(
            X_ptr + m_offsets[:, None] * stride_xm + k[None, :] * stride_xk,
            mask=m_mask[:, None] & k_mask[None, :],
            other=0.0,
            cache_modifier=".ca",
        )
        b = tl.load(
            W_ptr + k[:, None] * stride_wk + n_offsets[None, :] * stride_wn,
            mask=k_mask[:, None] & n_mask[None, :],
            other=0.0,
            cache_modifier=".cg",
        )
        acc += tl.dot(a, b)

    bias = tl.load(B_ptr + n_offsets, mask=n_mask, other=0.0, cache_modifier=".ca")
    acc = acc + bias[None, :]

    neg_inf = -float("inf")
    acc = tl.where(n_mask[None, :], acc, neg_inf)

    local_max = tl.max(acc, axis=1)
    local_sum = tl.sum(tl.exp(acc - local_max[:, None]), axis=1)

    t = tl.load(T_ptr + m_offsets, mask=m_mask, other=0).to(tl.int32)
    match = t[:, None] == n_offsets[None, :]
    tgt = tl.max(tl.where(match, acc, neg_inf), axis=1)

    out_idx = m_offsets * stride_pm + pid_b
    tl.store(out_max_ptr + out_idx, local_max, mask=m_mask)
    tl.store(out_sum_ptr + out_idx, local_sum, mask=m_mask)
    tl.store(out_tgt_ptr + out_idx, tgt, mask=m_mask)


@triton.jit
def _reduce_stats_kernel(
    pmax_ptr,
    psum_ptr,
    ptgt_ptr,
    out_ptr,
    M: tl.constexpr,
    stride_pm: tl.constexpr,
    nblocks: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCKS: tl.constexpr,
):
    pid = tl.program_id(0)
    m_offsets = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = m_offsets < M

    b_offsets = tl.arange(0, BLOCKS)
    b_mask = b_offsets < nblocks

    idx = m_offsets[:, None] * stride_pm + b_offsets[None, :]
    neg_inf = -float("inf")

    maxes = tl.load(pmax_ptr + idx, mask=m_mask[:, None] & b_mask[None, :], other=neg_inf)
    gmax = tl.max(maxes, axis=1)

    sums = tl.load(psum_ptr + idx, mask=m_mask[:, None] & b_mask[None, :], other=0.0)
    total = tl.sum(sums * tl.exp(maxes - gmax[:, None]), axis=1)

    tgts = tl.load(ptgt_ptr + idx, mask=m_mask[:, None] & b_mask[None, :], other=neg_inf)
    tgt = tl.max(tgts, axis=1)

    loss = gmax + tl.log(total) - tgt
    tl.store(out_ptr + m_offsets, loss, mask=m_mask)


_workspace_cache: Dict[Tuple[int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int]] = {}


def _get_workspace(device: torch.device, M: int, nblocks: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    dev_idx = device.index if device.index is not None else torch.cuda.current_device()
    key = (dev_idx, nblocks)
    entry = _workspace_cache.get(key, None)
    if entry is None or entry[3] < M:
        cap_m = max(M, entry[3] if entry is not None else 0)
        pmax = torch.empty((cap_m, nblocks), device=device, dtype=torch.float32)
        psum = torch.empty((cap_m, nblocks), device=device, dtype=torch.float32)
        ptgt = torch.empty((cap_m, nblocks), device=device, dtype=torch.float32)
        _workspace_cache[key] = (pmax, psum, ptgt, cap_m)
        return pmax[:M], psum[:M], ptgt[:M]
    return entry[0][:M], entry[1][:M], entry[2][:M]


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not X.is_cuda:
        logits = X.float() @ W.float()
        logits = logits + B.float()
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    M, K = X.shape
    K2, N = W.shape
    assert K2 == K
    assert B.shape[0] == N
    assert targets.shape[0] == M

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W.dtype != torch.float16:
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)
    if targets.dtype != torch.int64:
        targets = targets.to(torch.int64)

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()
    if not targets.is_contiguous():
        targets = targets.contiguous()

    BLOCK_N = 64
    nblocks = _ceil_div(N, BLOCK_N)

    pmax, psum, ptgt = _get_workspace(X.device, M, nblocks)
    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid1 = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]), nblocks)
    _partial_stats_kernel[grid1](
        X,
        W,
        B,
        targets,
        pmax,
        psum,
        ptgt,
        M=M,
        N=N,
        K=K,
        stride_xm=X.stride(0),
        stride_xk=X.stride(1),
        stride_wk=W.stride(0),
        stride_wn=W.stride(1),
        stride_pm=pmax.stride(0),
        BLOCK_N=BLOCK_N,
    )

    BLOCKS = _next_pow2(nblocks)
    if BLOCKS > 256:
        BLOCKS = 256
    grid2 = (triton.cdiv(M, 128),)
    _reduce_stats_kernel[grid2](
        pmax,
        psum,
        ptgt,
        out,
        M=M,
        stride_pm=pmax.stride(0),
        nblocks=nblocks,
        BLOCK_M=128,
        BLOCKS=BLOCKS,
        num_warps=4,
        num_stages=1,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                return {"code": f.read()}
        except Exception:
            return {"code": "import torch\nimport triton\nimport triton.language as tl\n\n# Failed to read source\n"}