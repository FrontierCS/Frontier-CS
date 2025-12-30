import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    out_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


@triton.jit
def _add_kernel_vectorized(
    x_ptr,
    y_ptr,
    out_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE * VECTOR_SIZE + tl.arange(0, BLOCK_SIZE * VECTOR_SIZE)
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.shape == y.shape and x.is_contiguous() and y.is_contiguous()
    assert x.dtype == y.dtype and x.device == y.device and x.device.type == "cuda"

    n_elements = x.numel()
    out = torch.empty_like(x)

    if n_elements % 1024 == 0:
        # Use vectorized kernel for better memory throughput
        VECTOR_SIZE = 4
        BLOCK_SIZE = 256
        grid = (triton.cdiv(n_elements, BLOCK_SIZE * VECTOR_SIZE),)
        _add_kernel_vectorized[grid](
            x, y, out, n_elements, BLOCK_SIZE=BLOCK_SIZE, VECTOR_SIZE=VECTOR_SIZE
        )
    else:
        # Fallback for non-divisible sizes
        BLOCK_SIZE = 1024
        grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
        _add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=BLOCK_SIZE)

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    out_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


@triton.jit
def _add_kernel_vectorized(
    x_ptr,
    y_ptr,
    out_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE * VECTOR_SIZE + tl.arange(0, BLOCK_SIZE * VECTOR_SIZE)
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.shape == y.shape and x.is_contiguous() and y.is_contiguous()
    assert x.dtype == y.dtype and x.device == y.device and x.device.type == "cuda"

    n_elements = x.numel()
    out = torch.empty_like(x)

    if n_elements % 1024 == 0:
        # Use vectorized kernel for better memory throughput
        VECTOR_SIZE = 4
        BLOCK_SIZE = 256
        grid = (triton.cdiv(n_elements, BLOCK_SIZE * VECTOR_SIZE),)
        _add_kernel_vectorized[grid](
            x, y, out, n_elements, BLOCK_SIZE=BLOCK_SIZE, VECTOR_SIZE=VECTOR_SIZE
        )
    else:
        # Fallback for non-divisible sizes
        BLOCK_SIZE = 1024
        grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
        _add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=BLOCK_SIZE)

    return out
"""
        return {"code": code}