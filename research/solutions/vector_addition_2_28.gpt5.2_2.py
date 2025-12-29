import os
import sys
import inspect
import torch
import triton
import triton.language as tl

_N_ELEMENTS = 1 << 28
_BLOCK = 2048
_ITERS = 4
_NUM_WARPS = 8
_NUM_STAGES = 4


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr):
    pid = tl.program_id(0)
    base = pid * (_BLOCK * _ITERS)

    x_base = x_ptr + base
    y_base = y_ptr + base
    o_base = out_ptr + base

    ar = tl.arange(0, _BLOCK)

    tl.static_assert((_N_ELEMENTS % (_BLOCK * _ITERS)) == 0)

    for i in tl.static_range(0, _ITERS):
        offs = ar + i * _BLOCK
        x = tl.load(x_base + offs, cache_modifier=".cg", eviction_policy="evict_first")
        y = tl.load(y_base + offs, cache_modifier=".cg", eviction_policy="evict_first")
        tl.store(o_base + offs, x + y, cache_modifier=".cg", eviction_policy="evict_first")


@torch.no_grad()
def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != _N_ELEMENTS or y.numel() != _N_ELEMENTS:
        raise ValueError(f"add expects vectors of length {_N_ELEMENTS}, got {x.numel()} and {y.numel()}")
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError(f"dtype mismatch: {x.dtype} vs {y.dtype}")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    out = torch.empty_like(x)
    grid = (_N_ELEMENTS // (_BLOCK * _ITERS),)
    _add_kernel[grid](x, y, out, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if "__file__" in globals():
            try:
                if os.path.exists(__file__):
                    return {"program_path": __file__}
            except Exception:
                pass
        try:
            return {"code": inspect.getsource(sys.modules[__name__])}
        except Exception:
            return {"code": ""}