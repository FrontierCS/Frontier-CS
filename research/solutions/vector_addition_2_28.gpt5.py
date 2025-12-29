import math
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x_vals = tl.load(x_ptr + offsets, mask=mask, other=0, cache_modifier='.cg')
    y_vals = tl.load(y_ptr + offsets, mask=mask, other=0, cache_modifier='.cg')
    out = x_vals + y_vals
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)

    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    if not (x.is_cuda and y.is_cuda):
        raise ValueError("Inputs must be CUDA tensors.")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape.")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype.")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    # Heuristic tuning based on dtype size for bandwidth-bound workloads
    bytes_per_el = x.element_size()
    if bytes_per_el <= 2:
        block_size = 16384
        num_warps = 8
        num_stages = 2
    elif bytes_per_el == 4:
        block_size = 8192
        num_warps = 8
        num_stages = 2
    else:
        block_size = 4096
        num_warps = 8
        num_stages = 2

    grid = (triton.cdiv(n, block_size),)

    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=block_size, num_warps=num_warps, num_stages=num_stages)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import math
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x_vals = tl.load(x_ptr + offsets, mask=mask, other=0, cache_modifier='.cg')
    y_vals = tl.load(y_ptr + offsets, mask=mask, other=0, cache_modifier='.cg')
    out = x_vals + y_vals
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)
    
    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    if not (x.is_cuda and y.is_cuda):
        raise ValueError("Inputs must be CUDA tensors.")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape.")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype.")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    # Heuristic tuning based on dtype size for bandwidth-bound workloads
    bytes_per_el = x.element_size()
    if bytes_per_el <= 2:
        block_size = 16384
        num_warps = 8
        num_stages = 2
    elif bytes_per_el == 4:
        block_size = 8192
        num_warps = 8
        num_stages = 2
    else:
        block_size = 4096
        num_warps = 8
        num_stages = 2

    grid = (triton.cdiv(n, block_size),)
    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=block_size, num_warps=num_warps, num_stages=num_stages)
    return out
'''
        return {"code": code}