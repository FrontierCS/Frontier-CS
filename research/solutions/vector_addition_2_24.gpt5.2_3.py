import os
import sys
import types
import torch
import triton
import triton.language as tl

KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl

VECTOR_SIZE = 1 << 24

@triton.jit
def _add_kernel_nomask(x_ptr, y_ptr, z_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    start = pid * BLOCK
    tl.multiple_of(start, 256)
    offs = start + tl.arange(0, BLOCK)
    tl.max_contiguous(offs, 256)
    x = tl.load(x_ptr + offs, cache_modifier=".cg")
    y = tl.load(y_ptr + offs, cache_modifier=".cg")
    tl.store(z_ptr + offs, x + y, cache_modifier=".cg")

@triton.jit
def _add_kernel_mask(x_ptr, y_ptr, z_ptr, n_elements, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    start = pid * BLOCK
    tl.multiple_of(start, 256)
    offs = start + tl.arange(0, BLOCK)
    tl.max_contiguous(offs, 256)
    mask = offs < n_elements
    x = tl.load(x_ptr + offs, mask=mask, other=0, cache_modifier=".cg")
    y = tl.load(y_ptr + offs, mask=mask, other=0, cache_modifier=".cg")
    tl.store(z_ptr + offs, x + y, mask=mask, cache_modifier=".cg")

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != "cuda":
        return x + y
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    itemsize = x.element_size()
    if itemsize == 2:
        BLOCK = 8192
        num_warps = 8
        num_stages = 4
    elif itemsize == 4:
        BLOCK = 4096
        num_warps = 8
        num_stages = 4
    else:
        BLOCK = 2048
        num_warps = 4
        num_stages = 3

    if n == VECTOR_SIZE and (n % BLOCK) == 0:
        grid = (n // BLOCK,)
        _add_kernel_nomask[grid](x, y, out, BLOCK=BLOCK, num_warps=num_warps, num_stages=num_stages)
    else:
        grid = (triton.cdiv(n, BLOCK),)
        _add_kernel_mask[grid](x, y, out, n, BLOCK=BLOCK, num_warps=num_warps, num_stages=num_stages)

    return out

__all__ = ["add"]
'''

exec(compile(KERNEL_CODE, "<triton_add_kernel>", "exec"), globals(), globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}