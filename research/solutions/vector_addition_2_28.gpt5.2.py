import os
import sys
import math
import textwrap
import torch
import triton
import triton.language as tl

_DEFAULT_BLOCK = 4096
_DEFAULT_NUM_WARPS = 8
_DEFAULT_NUM_STAGES = 4


@triton.jit
def _add_nomask_kernel(X_ptr, Y_ptr, Z_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK
    offs = block_start + tl.arange(0, BLOCK)
    x = tl.load(X_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(Y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(Z_ptr + offs, x + y, cache_modifier=".cg", eviction_policy="evict_last")


@triton.jit
def _add_mask_kernel(X_ptr, Y_ptr, Z_ptr, N, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK
    offs = block_start + tl.arange(0, BLOCK)
    mask = offs < N
    x = tl.load(X_ptr + offs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
    y = tl.load(Y_ptr + offs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
    tl.store(Z_ptr + offs, x + y, mask=mask, cache_modifier=".cg", eviction_policy="evict_last")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not x.is_cuda or not y.is_cuda:
        return x + y
    if x.dtype != y.dtype:
        raise TypeError(f"dtype mismatch: {x.dtype} vs {y.dtype}")
    if x.numel() != y.numel():
        raise ValueError("size mismatch")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    z = torch.empty_like(x)

    block = _DEFAULT_BLOCK
    num_warps = _DEFAULT_NUM_WARPS
    num_stages = _DEFAULT_NUM_STAGES

    if n % block == 0:
        grid = (n // block,)
        _add_nomask_kernel[grid](x, y, z, BLOCK=block, num_warps=num_warps, num_stages=num_stages)
    else:
        grid = (triton.cdiv(n, block),)
        _add_mask_kernel[grid](x, y, z, n, BLOCK=block, num_warps=num_warps, num_stages=num_stages)

    return z


_KERNEL_CODE = textwrap.dedent(
    """
    import torch
    import triton
    import triton.language as tl

    _DEFAULT_BLOCK = 4096
    _DEFAULT_NUM_WARPS = 8
    _DEFAULT_NUM_STAGES = 4

    @triton.jit
    def _add_nomask_kernel(X_ptr, Y_ptr, Z_ptr, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        block_start = pid * BLOCK
        offs = block_start + tl.arange(0, BLOCK)
        x = tl.load(X_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        y = tl.load(Y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        tl.store(Z_ptr + offs, x + y, cache_modifier=".cg", eviction_policy="evict_last")

    @triton.jit
    def _add_mask_kernel(X_ptr, Y_ptr, Z_ptr, N, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        block_start = pid * BLOCK
        offs = block_start + tl.arange(0, BLOCK)
        mask = offs < N
        x = tl.load(X_ptr + offs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
        y = tl.load(Y_ptr + offs, mask=mask, other=0, cache_modifier=".cg", eviction_policy="evict_last")
        tl.store(Z_ptr + offs, x + y, mask=mask, cache_modifier=".cg", eviction_policy="evict_last")

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if not x.is_cuda or not y.is_cuda:
            return x + y
        if x.dtype != y.dtype:
            raise TypeError(f"dtype mismatch: {x.dtype} vs {y.dtype}")
        if x.numel() != y.numel():
            raise ValueError("size mismatch")
        if not x.is_contiguous() or not y.is_contiguous():
            x = x.contiguous()
            y = y.contiguous()

        n = x.numel()
        z = torch.empty_like(x)

        block = _DEFAULT_BLOCK
        num_warps = _DEFAULT_NUM_WARPS
        num_stages = _DEFAULT_NUM_STAGES

        if n % block == 0:
            grid = (n // block,)
            _add_nomask_kernel[grid](x, y, z, BLOCK=block, num_warps=num_warps, num_stages=num_stages)
        else:
            grid = (triton.cdiv(n, block),)
            _add_mask_kernel[grid](x, y, z, n, BLOCK=block, num_warps=num_warps, num_stages=num_stages)

        return z
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}