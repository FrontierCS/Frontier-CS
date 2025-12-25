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
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")

    n = x.numel()
    if n == 0:
        return x + y

    # Fallback to PyTorch if not on CUDA
    if not (x.is_cuda and y.is_cuda):
        return x + y

    out = torch.empty_like(x)

    BLOCK_SIZE = 2048
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _vector_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''\
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
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")

    n = x.numel()
    if n == 0:
        return x + y

    if not (x.is_cuda and y.is_cuda):
        return x + y

    out = torch.empty_like(x)

    BLOCK_SIZE = 2048
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _vector_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
    return out
'''
        return {"code": code}
