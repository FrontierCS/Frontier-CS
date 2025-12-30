import torch
import triton
import triton.language as tl
from typing import Dict, Optional


@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using a Triton kernel.
    """
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")

    # Fallback to PyTorch if not on CUDA
    if not x.is_cuda:
        return x + y

    # For dtypes other than float32, fallback to PyTorch to avoid dtype handling complexity
    if x.dtype != torch.float32 or y.dtype != torch.float32:
        return x + y

    x_flat = x.view(-1)
    y_flat = y.view(-1)
    n_elements = x_flat.numel()

    out = torch.empty_like(x_flat)
    if n_elements == 0:
        return out.view_as(x)

    BLOCK_SIZE = 4096
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    add_kernel[grid](
        x_flat,
        y_flat,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4,
        num_stages=2,
    )

    return out.view_as(x)


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        kernel_code = '''import torch
import triton
import triton.language as tl


@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using a Triton kernel.
    """
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")

    # Fallback to PyTorch if not on CUDA
    if not x.is_cuda:
        return x + y

    # For dtypes other than float32, fallback to PyTorch to avoid dtype handling complexity
    if x.dtype != torch.float32 or y.dtype != torch.float32:
        return x + y

    x_flat = x.view(-1)
    y_flat = y.view(-1)
    n_elements = x_flat.numel()

    out = torch.empty_like(x_flat)
    if n_elements == 0:
        return out.view_as(x)

    BLOCK_SIZE = 4096
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    add_kernel[grid](
        x_flat,
        y_flat,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4,
        num_stages=2,
    )

    return out.view_as(x)
'''
        return {"code": kernel_code}