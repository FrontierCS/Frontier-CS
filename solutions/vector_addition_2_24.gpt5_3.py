import torch
import triton
import triton.language as tl


@triton.jit
def _vadd_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, VEC: tl.constexpr):
    pid = tl.program_id(0)
    base_idx = pid * BLOCK_SIZE * VEC + tl.arange(0, BLOCK_SIZE)
    for i in range(VEC):
        idx = base_idx + i * BLOCK_SIZE
        mask = idx < n_elements
        x = tl.load(x_ptr + idx, mask=mask, other=0)
        y = tl.load(y_ptr + idx, mask=mask, other=0)
        tl.store(out_ptr + idx, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.numel() == y.numel(), "Input sizes must match"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    VEC = 8
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE'] * meta['VEC']),)
    _vadd_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=BLOCK_SIZE, VEC=VEC, num_warps=8, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _vadd_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, VEC: tl.constexpr):
    pid = tl.program_id(0)
    base_idx = pid * BLOCK_SIZE * VEC + tl.arange(0, BLOCK_SIZE)
    for i in range(VEC):
        idx = base_idx + i * BLOCK_SIZE
        mask = idx < n_elements
        x = tl.load(x_ptr + idx, mask=mask, other=0)
        y = tl.load(y_ptr + idx, mask=mask, other=0)
        tl.store(out_ptr + idx, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.numel() == y.numel(), "Input sizes must match"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    VEC = 8
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE'] * meta['VEC']),)
    _vadd_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=BLOCK_SIZE, VEC=VEC, num_warps=8, num_stages=2)
    return out
'''
        return {"code": code}
