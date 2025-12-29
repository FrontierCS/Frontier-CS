import os
import math
import inspect
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


_LOG2E = 1.4426950408889634
_LN2 = 0.6931471805599453


def _get_autotune_configs():
    return [
        triton.Config({"BLOCK": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK": 512}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK": 1024}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK": 1024}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK": 2048}, num_warps=8, num_stages=3),
    ]


@triton.autotune(configs=_get_autotune_configs(), key=["N"])
@triton.jit
def _xent_kernel_contig(
    logits_ptr,
    targets_ptr,
    out_ptr,
    stride_m,
    N: tl.constexpr,
    BLOCK: tl.constexpr,
):
    pid = tl.program_id(0).to(tl.int64)
    row_ptr = logits_ptr + pid * stride_m

    cols = tl.arange(0, BLOCK)
    m = tl.full((), -float("inf"), tl.float32)
    s = tl.zeros((), dtype=tl.float32)

    n_blocks = tl.cdiv(N, BLOCK)
    for bi in tl.static_range(0, n_blocks):
        start = bi * BLOCK
        offs = start + cols
        mask = offs < N
        x = tl.load(row_ptr + offs, mask=mask, other=-float("inf")).to(tl.float32)

        b_m = tl.max(x, axis=0)
        b_s = tl.sum(tl.exp2((x - b_m) * _LOG2E), axis=0)

        new_m = tl.maximum(m, b_m)
        s = s * tl.exp2((m - new_m) * _LOG2E) + b_s * tl.exp2((b_m - new_m) * _LOG2E)
        m = new_m

    lse = tl.log2(s) * _LN2 + m

    t = tl.load(targets_ptr + pid).to(tl.int32)
    logit_t = tl.load(row_ptr + t, mask=t < N, other=-float("inf")).to(tl.float32)
    loss = lse - logit_t
    tl.store(out_ptr + pid, loss)


@triton.autotune(configs=_get_autotune_configs(), key=["N"])
@triton.jit
def _xent_kernel_strided(
    logits_ptr,
    targets_ptr,
    out_ptr,
    stride_m,
    stride_n,
    N: tl.constexpr,
    BLOCK: tl.constexpr,
):
    pid = tl.program_id(0).to(tl.int64)
    row_base = pid * stride_m

    cols = tl.arange(0, BLOCK)
    m = tl.full((), -float("inf"), tl.float32)
    s = tl.zeros((), dtype=tl.float32)

    n_blocks = tl.cdiv(N, BLOCK)
    for bi in tl.static_range(0, n_blocks):
        start = bi * BLOCK
        offs = start + cols
        mask = offs < N
        x = tl.load(logits_ptr + row_base + offs * stride_n, mask=mask, other=-float("inf")).to(tl.float32)

        b_m = tl.max(x, axis=0)
        b_s = tl.sum(tl.exp2((x - b_m) * _LOG2E), axis=0)

        new_m = tl.maximum(m, b_m)
        s = s * tl.exp2((m - new_m) * _LOG2E) + b_s * tl.exp2((b_m - new_m) * _LOG2E)
        m = new_m

    lse = tl.log2(s) * _LN2 + m

    t = tl.load(targets_ptr + pid).to(tl.int32)
    logit_t = tl.load(logits_ptr + row_base + t * stride_n, mask=t < N, other=-float("inf")).to(tl.float32)
    loss = lse - logit_t
    tl.store(out_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N); got shape={tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,); got shape={tuple(targets.shape)}")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError(f"M mismatch: logits.shape[0]={logits.shape[0]} vs targets.shape[0]={targets.shape[0]}")
    if targets.dtype not in (torch.int32, torch.int64):
        raise ValueError(f"targets must be int32 or int64; got {targets.dtype}")

    M, N = logits.shape
    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    if M == 0:
        return out

    if not logits.is_cuda:
        x = logits.to(torch.float32)
        t = targets.to(torch.int64)
        lse = torch.logsumexp(x, dim=1)
        picked = x[torch.arange(M, device=logits.device), t]
        return (lse - picked).to(torch.float32)

    if not targets.is_cuda:
        raise ValueError("targets must be on CUDA if logits is on CUDA")

    if not targets.is_contiguous():
        targets_ = targets.contiguous()
    else:
        targets_ = targets

    stride_m, stride_n = logits.stride()
    grid = (M,)

    if logits.is_contiguous() and stride_n == 1:
        _xent_kernel_contig[grid](
            logits,
            targets_,
            out,
            stride_m,
            N=N,
        )
    else:
        _xent_kernel_strided[grid](
            logits,
            targets_,
            out,
            stride_m,
            stride_n,
            N=N,
        )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}