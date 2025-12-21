import torch
import triton
import triton.language as tl


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x_vals = tl.load(x_ptr + offsets, mask=mask)
    y_vals = tl.load(y_ptr + offsets, mask=mask)
    out_vals = x_vals + y_vals
    tl.store(out_ptr + offsets, out_vals, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors x and y must have the same shape")
    if not x.is_cuda or not y.is_cuda:
        # Fallback to PyTorch for non-CUDA tensors
        return x + y

    x_contig = x.contiguous()
    y_contig = y.contiguous()

    x_flat = x_contig.view(-1)
    y_flat = y_contig.view(-1)
    n_elements = x_flat.numel()

    out = torch.empty_like(x_flat)

    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    _vector_add_kernel[grid](
        x_flat,
        y_flat,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=2,
    )

    return out.view_as(x_contig)


KERNEL_CODE = """
import torch
import triton
import triton.language as tl


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x_vals = tl.load(x_ptr + offsets, mask=mask)
    y_vals = tl.load(y_ptr + offsets, mask=mask)
    out_vals = x_vals + y_vals
    tl.store(out_ptr + offsets, out_vals, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors x and y must have the same shape")
    if not x.is_cuda or not y.is_cuda:
        # Fallback to PyTorch for non-CUDA tensors
        return x + y

    x_contig = x.contiguous()
    y_contig = y.contiguous()

    x_flat = x_contig.view(-1)
    y_flat = y_contig.view(-1)
    n_elements = x_flat.numel()

    out = torch.empty_like(x_flat)

    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    _vector_add_kernel[grid](
        x_flat,
        y_flat,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=2,
    )

    return out.view_as(x_contig)
"""


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
