import os
import textwrap
import torch
import triton
import triton.language as tl

_N = 1 << 20
_BLOCK = 1024
_NUM_WARPS = 4
_NUM_STAGES = 2


@triton.jit
def _add_kernel(x_ptr, y_ptr, o_ptr, BLOCK: tl.constexpr):
    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(o_ptr, 16)

    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)

    x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(o_ptr + offs, x + y)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"Expected vectors of length {_N}")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")
    if not (x.is_contiguous() and y.is_contiguous()):
        raise ValueError("x and y must be contiguous")

    if not x.is_cuda:
        return x + y

    out = torch.empty_like(x)
    grid = (_N // _BLOCK,)
    _add_kernel[grid](x, y, out, BLOCK=_BLOCK, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
    return out


_SOLUTION_CODE = textwrap.dedent(
    f"""
    import torch
    import triton
    import triton.language as tl

    _N = {1<<20}
    _BLOCK = {_BLOCK}
    _NUM_WARPS = {_NUM_WARPS}
    _NUM_STAGES = {_NUM_STAGES}

    @triton.jit
    def _add_kernel(x_ptr, y_ptr, o_ptr, BLOCK: tl.constexpr):
        tl.multiple_of(x_ptr, 16)
        tl.multiple_of(y_ptr, 16)
        tl.multiple_of(o_ptr, 16)

        pid = tl.program_id(0)
        offs = pid * BLOCK + tl.arange(0, BLOCK)
        x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        tl.store(o_ptr + offs, x + y)

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if x.numel() != _N or y.numel() != _N:
            raise ValueError(f"Expected vectors of length {{_N}}")
        if x.shape != y.shape:
            raise ValueError("x and y must have the same shape")
        if x.device != y.device:
            raise ValueError("x and y must be on the same device")
        if not (x.is_contiguous() and y.is_contiguous()):
            raise ValueError("x and y must be contiguous")

        if not x.is_cuda:
            return x + y

        out = torch.empty_like(x)
        grid = (_N // _BLOCK,)
        _add_kernel[grid](x, y, out, BLOCK=_BLOCK, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
        return out
    """
).strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _SOLUTION_CODE}