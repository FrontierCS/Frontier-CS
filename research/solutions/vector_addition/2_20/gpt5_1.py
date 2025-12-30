import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel_masked(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < n_elements
    x = tl.load(x_ptr + offs, mask=mask)
    y = tl.load(y_ptr + offs, mask=mask)
    z = x + y
    tl.store(out_ptr + offs, z, mask=mask)


@triton.jit
def _add_kernel_nomask(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    x = tl.load(x_ptr + offs)
    y = tl.load(y_ptr + offs)
    z = x + y
    tl.store(out_ptr + offs, z)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.shape == y.shape, "Input shapes must match"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    n_elements = x.numel()
    out = torch.empty_like(x)

    # Tuned for medium vectors on NVIDIA L4
    BLOCK_SIZE = 8192
    num_warps = 8
    num_stages = 1

    if n_elements % BLOCK_SIZE == 0:
        grid = (n_elements // BLOCK_SIZE,)
        _add_kernel_nomask[grid](
            x, y, out, n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    else:
        grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
        _add_kernel_masked[grid](
            x, y, out, n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel_masked(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < n_elements
    x = tl.load(x_ptr + offs, mask=mask)
    y = tl.load(y_ptr + offs, mask=mask)
    z = x + y
    tl.store(out_ptr + offs, z, mask=mask)


@triton.jit
def _add_kernel_nomask(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    x = tl.load(x_ptr + offs)
    y = tl.load(y_ptr + offs)
    z = x + y
    tl.store(out_ptr + offs, z)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.shape == y.shape, "Input shapes must match"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    n_elements = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 8192
    num_warps = 8
    num_stages = 1

    if n_elements % BLOCK_SIZE == 0:
        grid = (n_elements // BLOCK_SIZE,)
        _add_kernel_nomask[grid](
            x, y, out, n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    else:
        grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
        _add_kernel_masked[grid](
            x, y, out, n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    return out
'''
        return {"code": code}