import os
import textwrap
import torch
import triton
import triton.language as tl

_VECTOR_SIZE = 1 << 20
_BLOCK_SIZE = 4096
_NUM_WARPS = 8
_NUM_STAGES = 4


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    tl.multiple_of(offs, 16)
    x = tl.load(x_ptr + offs)
    y = tl.load(y_ptr + offs)
    tl.store(out_ptr + offs, x + y)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.numel() != _VECTOR_SIZE or y.numel() != _VECTOR_SIZE:
        raise ValueError(f"Expected tensors with numel={_VECTOR_SIZE}")
    if x.dtype != y.dtype:
        return x + y
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    out = torch.empty_like(x)
    grid = (_VECTOR_SIZE // _BLOCK_SIZE,)
    _add_kernel[grid](x, y, out, BLOCK=_BLOCK_SIZE, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
    return out


_KERNEL_CODE = textwrap.dedent(
    f"""
    import torch
    import triton
    import triton.language as tl

    _VECTOR_SIZE = {1<<20}
    _BLOCK_SIZE = {4096}
    _NUM_WARPS = {8}
    _NUM_STAGES = {4}

    @triton.jit
    def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        offs = pid * BLOCK + tl.arange(0, BLOCK)
        tl.multiple_of(offs, 16)
        x = tl.load(x_ptr + offs)
        y = tl.load(y_ptr + offs)
        tl.store(out_ptr + offs, x + y)

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
            raise TypeError("x and y must be torch.Tensor")
        if x.device.type != "cuda" or y.device.type != "cuda":
            return x + y
        if x.numel() != _VECTOR_SIZE or y.numel() != _VECTOR_SIZE:
            raise ValueError(f"Expected tensors with numel={{_VECTOR_SIZE}}")
        if x.dtype != y.dtype:
            return x + y
        if not x.is_contiguous() or not y.is_contiguous():
            x = x.contiguous()
            y = y.contiguous()

        out = torch.empty_like(x)
        grid = (_VECTOR_SIZE // _BLOCK_SIZE,)
        _add_kernel[grid](x, y, out, BLOCK=_BLOCK_SIZE, num_warps=_NUM_WARPS, num_stages=_NUM_STAGES)
        return out
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}