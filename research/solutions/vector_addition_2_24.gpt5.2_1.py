import os
import textwrap
import torch
import triton
import triton.language as tl

_N_ELEMENTS = 1 << 24


@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    out_ptr,
    BLOCK: tl.constexpr,
    UNROLL: tl.constexpr,
):
    pid = tl.program_id(0)
    base = pid * BLOCK * UNROLL

    tl.multiple_of(base, BLOCK)
    tl.multiple_of(base, 32)

    r = tl.arange(0, BLOCK)
    tl.multiple_of(r, 1)
    tl.max_contiguous(r, BLOCK)

    for i in tl.static_range(UNROLL):
        offs = base + i * BLOCK + r
        tl.max_contiguous(offs, BLOCK)
        x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
        y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
        tl.store(out_ptr + offs, x + y, cache_modifier=".cg", eviction_policy="evict_first")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensors")
    if x.numel() != _N_ELEMENTS or y.numel() != _N_ELEMENTS:
        raise ValueError(f"Expected tensors with numel == {_N_ELEMENTS}")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.dim() != 1 or y.dim() != 1:
        x = x.view(-1)
        y = y.view(-1)
        if x.numel() != _N_ELEMENTS or y.numel() != _N_ELEMENTS:
            raise ValueError(f"Expected tensors with numel == {_N_ELEMENTS}")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("x and y must be contiguous")

    if not x.is_cuda:
        return x + y

    out = torch.empty_like(x)

    BLOCK = 256
    UNROLL = 8
    grid = (_N_ELEMENTS // (BLOCK * UNROLL),)

    _add_kernel[grid](
        x,
        y,
        out,
        BLOCK=BLOCK,
        UNROLL=UNROLL,
        num_warps=8,
        num_stages=1,
    )
    return out


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    _N_ELEMENTS = 1 << 24

    @triton.jit
    def _add_kernel(
        x_ptr,
        y_ptr,
        out_ptr,
        BLOCK: tl.constexpr,
        UNROLL: tl.constexpr,
    ):
        pid = tl.program_id(0)
        base = pid * BLOCK * UNROLL

        tl.multiple_of(base, BLOCK)
        tl.multiple_of(base, 32)

        r = tl.arange(0, BLOCK)
        tl.multiple_of(r, 1)
        tl.max_contiguous(r, BLOCK)

        for i in tl.static_range(UNROLL):
            offs = base + i * BLOCK + r
            tl.max_contiguous(offs, BLOCK)
            x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
            y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
            tl.store(out_ptr + offs, x + y, cache_modifier=".cg", eviction_policy="evict_first")

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
            raise TypeError("x and y must be torch.Tensors")
        if x.numel() != _N_ELEMENTS or y.numel() != _N_ELEMENTS:
            raise ValueError(f"Expected tensors with numel == {_N_ELEMENTS}")
        if x.device != y.device:
            raise ValueError("x and y must be on the same device")
        if x.dtype != y.dtype:
            raise ValueError("x and y must have the same dtype")
        if x.dim() != 1 or y.dim() != 1:
            x = x.view(-1)
            y = y.view(-1)
            if x.numel() != _N_ELEMENTS or y.numel() != _N_ELEMENTS:
                raise ValueError(f"Expected tensors with numel == {_N_ELEMENTS}")
        if not x.is_contiguous() or not y.is_contiguous():
            raise ValueError("x and y must be contiguous")

        if not x.is_cuda:
            return x + y

        out = torch.empty_like(x)

        BLOCK = 256
        UNROLL = 8
        grid = (_N_ELEMENTS // (BLOCK * UNROLL),)

        _add_kernel[grid](
            x,
            y,
            out,
            BLOCK=BLOCK,
            UNROLL=UNROLL,
            num_warps=8,
            num_stages=1,
        )
        return out
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}