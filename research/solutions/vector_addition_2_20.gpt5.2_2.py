import os
import sys
import torch
import triton
import triton.language as tl

_N = 1048576
_BLOCK = 4096


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK

    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(out_ptr, 16)
    tl.multiple_of(block_start, 256)

    offsets = block_start + tl.arange(0, BLOCK)
    x = tl.load(x_ptr + offsets, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(y_ptr + offsets, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(out_ptr + offsets, x + y, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not x.is_cuda:
        return x + y
    out = torch.empty_like(x)
    grid = (_N // _BLOCK,)
    _add_kernel[grid](x, y, out, BLOCK=_BLOCK, num_warps=8, num_stages=2)
    return out


_KERNEL_CODE = (
    "import torch\n"
    "import triton\n"
    "import triton.language as tl\n"
    "\n"
    "_N = 1048576\n"
    "_BLOCK = 4096\n"
    "\n"
    "@triton.jit\n"
    "def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):\n"
    "    pid = tl.program_id(axis=0)\n"
    "    block_start = pid * BLOCK\n"
    "    tl.multiple_of(x_ptr, 16)\n"
    "    tl.multiple_of(y_ptr, 16)\n"
    "    tl.multiple_of(out_ptr, 16)\n"
    "    tl.multiple_of(block_start, 256)\n"
    "    offsets = block_start + tl.arange(0, BLOCK)\n"
    "    x = tl.load(x_ptr + offsets, cache_modifier='.cg', eviction_policy='evict_last')\n"
    "    y = tl.load(y_ptr + offsets, cache_modifier='.cg', eviction_policy='evict_last')\n"
    "    tl.store(out_ptr + offsets, x + y, cache_modifier='.cg')\n"
    "\n"
    "def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:\n"
    "    if not x.is_cuda:\n"
    "        return x + y\n"
    "    out = torch.empty_like(x)\n"
    "    grid = (_N // _BLOCK,)\n"
    "    _add_kernel[grid](x, y, out, BLOCK=_BLOCK, num_warps=8, num_stages=2)\n"
    "    return out\n"
)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}