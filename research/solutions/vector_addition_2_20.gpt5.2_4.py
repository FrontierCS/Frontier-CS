import os
import types

KERNEL_SRC = r'''
import torch
import triton
import triton.language as tl

_N = 1 << 20
_BLOCK = 4096
_NUM_WARPS = 8

@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK

    # Alignment / contiguity hints
    tl.multiple_of(block_start, 256)
    base_x = x_ptr + block_start
    base_y = y_ptr + block_start
    base_o = out_ptr + block_start
    tl.multiple_of(base_x, 16)
    tl.multiple_of(base_y, 16)
    tl.multiple_of(base_o, 16)

    r = tl.arange(0, BLOCK)
    tl.max_contiguous(r, 256)
    offs = block_start + r

    x = tl.load(base_x + r, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(base_y + r, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(base_o + r, x + y)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not x.is_cuda:
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"Expected tensors with exactly {_N} elements")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("x and y must be contiguous")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")

    out = torch.empty_like(x)
    grid = (_N // _BLOCK,)
    _add_kernel[grid](x, y, out, BLOCK=_BLOCK, num_warps=_NUM_WARPS, num_stages=1)
    return out
'''

exec(compile(KERNEL_SRC, "<triton_add_kernel>", "exec"), globals(), globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_SRC}