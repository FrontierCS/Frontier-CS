import os
import torch
import triton
import triton.language as tl

_N_EXPECTED = 1 << 28
_BLOCK = 4096


@triton.jit
def _add_kernel_fast(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    x_ptrs = x_ptr + offs
    y_ptrs = y_ptr + offs
    out_ptrs = out_ptr + offs

    tl.multiple_of(x_ptrs, 16)
    tl.multiple_of(y_ptrs, 16)
    tl.multiple_of(out_ptrs, 16)
    tl.max_contiguous(offs, 256)

    x = tl.load(x_ptrs, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(y_ptrs, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(out_ptrs, x + y, cache_modifier=".cg")


@triton.jit
def _add_kernel_masked(x_ptr, y_ptr, out_ptr, n_elements, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n_elements
    x_ptrs = x_ptr + offs
    y_ptrs = y_ptr + offs
    out_ptrs = out_ptr + offs

    tl.multiple_of(x_ptrs, 16)
    tl.multiple_of(y_ptrs, 16)
    tl.multiple_of(out_ptrs, 16)
    tl.max_contiguous(offs, 256)

    x = tl.load(x_ptrs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(y_ptrs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(out_ptrs, x + y, mask=mask, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    num_warps = 8
    num_stages = 2

    if n % _BLOCK == 0:
        grid = (n // _BLOCK,)
        _add_kernel_fast[grid](x, y, out, BLOCK=_BLOCK, num_warps=num_warps, num_stages=num_stages)
    else:
        grid = (triton.cdiv(n, _BLOCK),)
        _add_kernel_masked[grid](x, y, out, n, BLOCK=_BLOCK, num_warps=num_warps, num_stages=num_stages)

    return out


_KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl

_BLOCK = 4096

@triton.jit
def _add_kernel_fast(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    x_ptrs = x_ptr + offs
    y_ptrs = y_ptr + offs
    out_ptrs = out_ptr + offs

    tl.multiple_of(x_ptrs, 16)
    tl.multiple_of(y_ptrs, 16)
    tl.multiple_of(out_ptrs, 16)
    tl.max_contiguous(offs, 256)

    x = tl.load(x_ptrs, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(y_ptrs, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(out_ptrs, x + y, cache_modifier=".cg")


@triton.jit
def _add_kernel_masked(x_ptr, y_ptr, out_ptr, n_elements, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n_elements
    x_ptrs = x_ptr + offs
    y_ptrs = y_ptr + offs
    out_ptrs = out_ptr + offs

    tl.multiple_of(x_ptrs, 16)
    tl.multiple_of(y_ptrs, 16)
    tl.multiple_of(out_ptrs, 16)
    tl.max_contiguous(offs, 256)

    x = tl.load(x_ptrs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(y_ptrs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(out_ptrs, x + y, mask=mask, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    num_warps = 8
    num_stages = 2

    if n % _BLOCK == 0:
        grid = (n // _BLOCK,)
        _add_kernel_fast[grid](x, y, out, BLOCK=_BLOCK, num_warps=num_warps, num_stages=num_stages)
    else:
        grid = (triton.cdiv(n, _BLOCK),)
        _add_kernel_masked[grid](x, y, out, n, BLOCK=_BLOCK, num_warps=num_warps, num_stages=num_stages)

    return out
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}