import os
import sys
import inspect
import pathlib
import torch
import triton
import triton.language as tl

_N_ELEMS = 268435456


@triton.jit
def _add_kernel(x_ptr, y_ptr, z_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)

    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(z_ptr, 16)
    tl.max_contiguous(offs, BLOCK)

    x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
    y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
    tl.store(z_ptr + offs, x + y)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("x and y must be CUDA tensors")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.numel() != _N_ELEMS or y.numel() != _N_ELEMS:
        raise ValueError(f"x and y must have exactly {_N_ELEMS} elements")
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError("x and y must be 1D tensors")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("x and y must be contiguous")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")

    z = torch.empty_like(x)

    if x.dtype in (torch.float16, torch.bfloat16):
        BLOCK = 16384
        NUM_WARPS = 8
    elif x.dtype == torch.float32:
        BLOCK = 8192
        NUM_WARPS = 8
    elif x.dtype == torch.float64:
        BLOCK = 4096
        NUM_WARPS = 8
    else:
        BLOCK = 8192
        NUM_WARPS = 8

    grid = (_N_ELEMS // BLOCK,)

    _add_kernel[grid](x, y, z, BLOCK=BLOCK, num_warps=NUM_WARPS, num_stages=1)
    return z


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            p = pathlib.Path(__file__)
            code = p.read_text()
        except Exception:
            try:
                code = inspect.getsource(sys.modules[__name__])
            except Exception:
                code = ""
        return {"code": code}