import os
import sys
import inspect
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


_N_ELEMS = 1048576
_BLOCK = 1024


if triton is not None:

    @triton.jit
    def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        offs = pid * BLOCK + tl.arange(0, BLOCK)
        tl.multiple_of(x_ptr, 16)
        tl.multiple_of(y_ptr, 16)
        tl.multiple_of(out_ptr, 16)
        x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        tl.store(out_ptr + offs, x + y, cache_modifier=".cg", eviction_policy="evict_last")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if triton is None or not x.is_cuda or not y.is_cuda:
        return x + y
    if x.numel() != _N_ELEMS or y.numel() != _N_ELEMS:
        return x + y
    if not x.is_contiguous() or not y.is_contiguous():
        return x + y
    if x.dtype != y.dtype:
        return x + y
    out = torch.empty_like(x)
    grid = (_N_ELEMS // _BLOCK,)
    _add_kernel[grid](x, y, out, BLOCK=_BLOCK, num_warps=8, num_stages=1)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            with open(path, "r", encoding="utf-8") as f:
                return {"code": f.read()}
        except Exception:
            try:
                return {"code": inspect.getsource(sys.modules[__name__])}
            except Exception:
                return {"code": ""}