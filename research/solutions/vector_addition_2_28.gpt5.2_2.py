import os
import sys
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


_N_ELEMS = 268_435_456  # 2^28


@triton.jit
def _add_kernel_streaming(
    x_ptr,
    y_ptr,
    out_ptr,
    BLOCK: tl.constexpr,
    CHUNK: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    base = pid * BLOCK

    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(out_ptr, 16)

    r = tl.arange(0, CHUNK)
    # BLOCK and CHUNK are compile-time constants; static_range is unrolled
    for i in tl.static_range(0, BLOCK, CHUNK):
        offs = base + i + r
        tl.max_contiguous(offs, CHUNK)
        x = tl.load(x_ptr + offs, cache_modifier=".cg")
        y = tl.load(y_ptr + offs, cache_modifier=".cg")
        tl.store(out_ptr + offs, x + y, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != _N_ELEMS or y.numel() != _N_ELEMS:
        raise ValueError(f"x and y must have exactly {_N_ELEMS} elements")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()
    if x.dim() != 1 or y.dim() != 1:
        x = x.view(-1)
        y = y.view(-1)

    out = torch.empty_like(x)

    BLOCK = 8192
    CHUNK = 1024
    grid = (_N_ELEMS // BLOCK,)

    _add_kernel_streaming[grid](
        x,
        y,
        out,
        BLOCK=BLOCK,
        CHUNK=CHUNK,
        num_warps=8,
        num_stages=4,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        if "__file__" in globals() and __file__:
            try:
                with open(__file__, "r", encoding="utf-8") as f:
                    return {"code": f.read()}
            except Exception:
                pass
            try:
                return {"program_path": os.path.abspath(__file__)}
            except Exception:
                pass
        return {"code": ""}