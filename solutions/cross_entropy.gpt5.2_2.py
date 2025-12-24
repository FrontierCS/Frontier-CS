import os
import sys
import math
import inspect
from typing import Optional, Dict

import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 2048}, num_warps=4, num_stages=3),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=3),
        ],
        key=["N"],
    )
    @triton.jit
    def _xent_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        M,
        stride_lm,
        stride_ln,
        stride_t,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid = tl.program_id(0)
        mask_m = pid < M

        pid64 = pid.to(tl.int64)
        stride_lm64 = stride_lm.to(tl.int64)
        stride_ln64 = stride_ln.to(tl.int64)
        stride_t64 = stride_t.to(tl.int64)

        row_start = pid64 * stride_lm64

        t = tl.load(targets_ptr + pid64 * stride_t64, mask=mask_m, other=0).to(tl.int64)
        logit_t = tl.load(logits_ptr + row_start + t * stride_ln64, mask=mask_m, other=-float("inf")).to(tl.float32)

        m = tl.full([1], -float("inf"), tl.float32)[0]
        s = tl.zeros([1], dtype=tl.float32)[0]

        ar = tl.arange(0, BLOCK_N)

        for col in tl.static_range(0, N, BLOCK_N):
            cols = col + ar
            in_bounds = cols < N
            ptrs = logits_ptr + row_start + cols.to(tl.int64) * stride_ln64
            x = tl.load(ptrs, mask=mask_m & in_bounds, other=-float("inf")).to(tl.float32)

            block_max = tl.max(x, axis=0)
            new_m = tl.maximum(m, block_max)
            s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
            m = new_m

        lse = tl.log(s) + m
        loss = lse - logit_t
        tl.store(out_ptr + pid, loss, mask=mask_m)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if triton is None:
        import torch.nn.functional as F
        return F.cross_entropy(logits, targets.to(torch.long), reduction="none").to(torch.float32)

    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N), got shape={tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,), got shape={tuple(targets.shape)}")

    if not logits.is_cuda or not targets.is_cuda:
        raise ValueError("logits and targets must be CUDA tensors")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError(f"targets length must equal M; got {targets.shape[0]} vs M={M}")

    if targets.dtype != torch.long:
        targets = targets.to(torch.long)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    grid = (M,)
    _xent_kernel[grid](
        logits,
        targets,
        out,
        M,
        logits.stride(0),
        logits.stride(1),
        targets.stride(0),
        N=N,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            if path is None:
                raise RuntimeError("__file__ is None")
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception:
            code = inspect.getsource(sys.modules[__name__])
        return {"code": code}
