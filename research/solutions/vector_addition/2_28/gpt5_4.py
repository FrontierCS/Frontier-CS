import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, cache_modifier=".cg")
    y = tl.load(y_ptr + offsets, mask=mask, cache_modifier=".cg")
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    n = x.numel()

    if n == 0:
        return torch.empty_like(x)

    if not x.is_cuda or not y.is_cuda:
        return x + y

    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("Input tensors must be contiguous")

    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=4)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, cache_modifier=".cg")
    y = tl.load(y_ptr + offsets, mask=mask, cache_modifier=".cg")
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    n = x.numel()

    if n == 0:
        return torch.empty_like(x)

    if not x.is_cuda or not y.is_cuda:
        return x + y

    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("Input tensors must be contiguous")

    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=4)
    return out
'''
        return {"code": code}