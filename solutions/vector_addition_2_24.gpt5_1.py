import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, o_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(o_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.shape == y.shape and x.ndim == 1, "Inputs must be 1D tensors of the same shape"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.dtype == y.dtype, "Input dtypes must match"

    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096  # 4K elements per program; aligns perfectly with 2^24 size
    grid = lambda META: (triton.cdiv(n, META['BLOCK_SIZE']),)
    num_warps = 8
    num_stages = 2

    _vec_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=num_warps, num_stages=num_stages)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, o_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(o_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.shape == y.shape and x.ndim == 1, "Inputs must be 1D tensors of the same shape"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.dtype == y.dtype, "Input dtypes must match"

    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096  # 4K elements per program; aligns perfectly with 2^24 size
    grid = lambda META: (triton.cdiv(n, META['BLOCK_SIZE']),)
    num_warps = 8
    num_stages = 2

    _vec_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=num_warps, num_stages=num_stages)
    return out
'''
        return {"code": code}
