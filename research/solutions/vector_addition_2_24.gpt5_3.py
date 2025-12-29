import torch
import triton
import triton.language as tl


@triton.jit
def _vadd_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.shape == y.shape, "Input tensors must have the same shape"
    assert x.is_cuda and y.is_cuda, "Inputs must be on CUDA device"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.dtype == y.dtype, "Input tensors must have the same dtype"
    n_elements = x.numel()
    out = torch.empty_like(x)
    BLOCK_SIZE = 4096  # 2^12, divides 2^24 exactly; good balance of occupancy and overhead
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    _vadd_kernel[grid](
        x, y, out, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=2
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _vadd_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.shape == y.shape, "Input tensors must have the same shape"
    assert x.is_cuda and y.is_cuda, "Inputs must be on CUDA device"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.dtype == y.dtype, "Input tensors must have the same dtype"
    n_elements = x.numel()
    out = torch.empty_like(x)
    BLOCK_SIZE = 4096  # 2^12, divides 2^24 exactly; good balance of occupancy and overhead
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    _vadd_kernel[grid](
        x, y, out, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=2
    )
    return out
'''
        return {"code": kernel_code}