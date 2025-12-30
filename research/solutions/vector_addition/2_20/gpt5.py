import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, EVEN_DIVISIBLE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    if EVEN_DIVISIBLE:
        x = tl.load(x_ptr + offsets)
        y = tl.load(y_ptr + offsets)
        tl.store(out_ptr + offsets, x + y)
    else:
        mask = offsets < n_elements
        x = tl.load(x_ptr + offsets, mask=mask, other=0)
        y = tl.load(y_ptr + offsets, mask=mask, other=0)
        tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)

    Returns:
        Output tensor of shape (1048576,) with x + y
    """
    if not (x.is_cuda and y.is_cuda):
        raise ValueError("Inputs must be CUDA tensors.")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype.")
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements.")
    if x.dim() != 1 or y.dim() != 1:
        raise ValueError("Input tensors must be 1D vectors.")

    n_elements = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    num_warps = 8
    num_stages = 4

    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    even_divisible = (n_elements % BLOCK_SIZE) == 0

    _add_kernel[grid](
        x, y, out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        EVEN_DIVISIBLE=even_divisible,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, EVEN_DIVISIBLE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    if EVEN_DIVISIBLE:
        x = tl.load(x_ptr + offsets)
        y = tl.load(y_ptr + offsets)
        tl.store(out_ptr + offsets, x + y)
    else:
        mask = offsets < n_elements
        x = tl.load(x_ptr + offsets, mask=mask, other=0)
        y = tl.load(y_ptr + offsets, mask=mask, other=0)
        tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)

    Returns:
        Output tensor of shape (1048576,) with x + y
    """
    if not (x.is_cuda and y.is_cuda):
        raise ValueError("Inputs must be CUDA tensors.")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype.")
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements.")
    if x.dim() != 1 or y.dim() != 1:
        raise ValueError("Input tensors must be 1D vectors.")

    n_elements = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    num_warps = 8
    num_stages = 4

    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    even_divisible = (n_elements % BLOCK_SIZE) == 0

    _add_kernel[grid](
        x, y, out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        EVEN_DIVISIBLE=even_divisible,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return out
'''
        return {"code": code}