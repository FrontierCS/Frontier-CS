import os
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, EVEN_N: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    if EVEN_N:
        x = tl.load(x_ptr + offsets)
        y = tl.load(y_ptr + offsets)
        tl.store(out_ptr + offsets, x + y)
    else:
        mask = offsets < n_elements
        x = tl.load(x_ptr + offsets, mask=mask)
        y = tl.load(y_ptr + offsets, mask=mask)
        tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("Inputs must be torch.Tensor")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")
    if x.numel() == 0:
        return x + y
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    if not x.is_cuda or not y.is_cuda:
        # Fallback to PyTorch if tensors are on CPU
        return x + y

    n = x.numel()
    out = torch.empty_like(x)

    # Choose a power-of-two block size that divides 2^28, aiding in mask-free fast path
    BLOCK_SIZE = 8192  # 2^13, divides 2^28 exactly
    EVEN_N = (n % BLOCK_SIZE == 0)

    grid = (triton.cdiv(n, BLOCK_SIZE),)
    _vec_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, EVEN_N=EVEN_N, num_warps=8, num_stages=3)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, EVEN_N: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    if EVEN_N:
        x = tl.load(x_ptr + offsets)
        y = tl.load(y_ptr + offsets)
        tl.store(out_ptr + offsets, x + y)
    else:
        mask = offsets < n_elements
        x = tl.load(x_ptr + offsets, mask=mask)
        y = tl.load(y_ptr + offsets, mask=mask)
        tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("Inputs must be torch.Tensor")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")
    if x.numel() == 0:
        return x + y
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    if not x.is_cuda or not y.is_cuda:
        # Fallback to PyTorch if tensors are on CPU
        return x + y

    n = x.numel()
    out = torch.empty_like(x)

    # Choose a power-of-two block size that divides 2^28, aiding in mask-free fast path
    BLOCK_SIZE = 8192  # 2^13, divides 2^28 exactly
    EVEN_N = (n % BLOCK_SIZE == 0)

    grid = (triton.cdiv(n, BLOCK_SIZE),)
    _vec_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, EVEN_N=EVEN_N, num_warps=8, num_stages=3)
    return out
'''
        return {"code": code}