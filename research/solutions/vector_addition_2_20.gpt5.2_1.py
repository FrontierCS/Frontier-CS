import os
import textwrap
import torch
import triton
import triton.language as tl

_N = 1048576
_BLOCK_SIZE = 4096
_NUM_WARPS = 8
_NUM_STAGES = 2


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    tl.multiple_of(offs, 16)
    x = tl.load(x_ptr + offs, cache_modifier="cg")
    y = tl.load(y_ptr + offs, cache_modifier="cg")
    tl.store(out_ptr + offs, x + y)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"Expected tensors with exactly {_N} elements")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.is_cuda:
        out = torch.empty_like(x)
        grid = (_N // _BLOCK_SIZE,)
        _add_kernel[grid](x, y, out, BLOCK=_BLOCK_SIZE, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
        return out
    return x + y


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    _N = 1048576
    _BLOCK_SIZE = 4096
    _NUM_WARPS = 8
    _NUM_STAGES = 2

    @triton.jit
    def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        offs = pid * BLOCK + tl.arange(0, BLOCK)
        tl.multiple_of(offs, 16)
        x = tl.load(x_ptr + offs, cache_modifier="cg")
        y = tl.load(y_ptr + offs, cache_modifier="cg")
        tl.store(out_ptr + offs, x + y)

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
            raise TypeError("x and y must be torch.Tensor")
        if x.numel() != _N or y.numel() != _N:
            raise ValueError(f"Expected tensors with exactly {_N} elements")
        if x.device != y.device:
            raise ValueError("x and y must be on the same device")
        if x.dtype != y.dtype:
            raise ValueError("x and y must have the same dtype")
        if x.is_cuda:
            out = torch.empty_like(x)
            grid = (_N // _BLOCK_SIZE,)
            _add_kernel[grid](x, y, out, BLOCK=_BLOCK_SIZE, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
            return out
        return x + y
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}