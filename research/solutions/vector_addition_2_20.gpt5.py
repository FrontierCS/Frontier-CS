import torch
import triton
import triton.language as tl


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")
    n = x.numel()
    if not x.is_cuda or not y.is_cuda:
        return x + y
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
    out = torch.empty_like(x)
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _vector_add_kernel[grid](x, y, out, n, BLOCK_SIZE=8192, num_warps=8, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")
    n = x.numel()
    if not x.is_cuda or not y.is_cuda:
        return x + y
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
    out = torch.empty_like(x)
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _vector_add_kernel[grid](x, y, out, n, BLOCK_SIZE=8192, num_warps=8, num_stages=2)
    return out
"""
        return {"code": code}
