import os
import textwrap
import torch
import triton
import triton.language as tl

@triton.jit
def _add_kernel(x_ptr, y_ptr, z_ptr, N: tl.constexpr, BLOCK: tl.constexpr):
    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(z_ptr, 16)

    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)

    x = tl.load(x_ptr + offs, mask=offs < N, other=0, cache_modifier=".cg", eviction_policy="evict_first")
    y = tl.load(y_ptr + offs, mask=offs < N, other=0, cache_modifier=".cg", eviction_policy="evict_first")
    tl.store(z_ptr + offs, x + y, mask=offs < N, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensors")
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    N = x.numel()
    z = torch.empty_like(x)

    BLOCK = 4096
    grid = (triton.cdiv(N, BLOCK),)
    _add_kernel[grid](x, y, z, N=N, BLOCK=BLOCK, num_warps=8, num_stages=4)
    return z


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def _add_kernel(x_ptr, y_ptr, z_ptr, N: tl.constexpr, BLOCK: tl.constexpr):
        tl.multiple_of(x_ptr, 16)
        tl.multiple_of(y_ptr, 16)
        tl.multiple_of(z_ptr, 16)

        pid = tl.program_id(0)
        offs = pid * BLOCK + tl.arange(0, BLOCK)

        x = tl.load(x_ptr + offs, mask=offs < N, other=0, cache_modifier=".cg", eviction_policy="evict_first")
        y = tl.load(y_ptr + offs, mask=offs < N, other=0, cache_modifier=".cg", eviction_policy="evict_first")
        tl.store(z_ptr + offs, x + y, mask=offs < N, cache_modifier=".cg")

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
            raise TypeError("x and y must be torch.Tensors")
        if x.device.type != "cuda" or y.device.type != "cuda":
            return x + y
        if x.dtype != y.dtype:
            raise TypeError("x and y must have the same dtype")
        if x.numel() != y.numel():
            raise ValueError("x and y must have the same number of elements")
        if not x.is_contiguous() or not y.is_contiguous():
            x = x.contiguous()
            y = y.contiguous()

        N = x.numel()
        z = torch.empty_like(x)

        BLOCK = 4096
        grid = (triton.cdiv(N, BLOCK),)
        _add_kernel[grid](x, y, z, N=N, BLOCK=BLOCK, num_warps=8, num_stages=4)
        return z
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}