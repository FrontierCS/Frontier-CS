import torch
import triton
import triton.language as tl

KERNEL_CODE = """
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=8, num_stages=2),
    ],
    key=['n_elements'],
)
@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    out_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(out_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"""
    Element-wise addition of two vectors.

    Args:
        x: Input tensor
        y: Input tensor

    Returns:
        Output tensor with x + y
    \"""
    if x.device.type != 'cuda' or y.device.type != 'cuda':
        raise ValueError('Input tensors must be CUDA tensors.')
    if x.shape != y.shape:
        raise ValueError('Input tensors must have the same shape.')
    if x.dtype != y.dtype:
        raise ValueError('Input tensors must have the same dtype.')

    x_contig = x.contiguous()
    y_contig = y.contiguous()
    n_elements = x_contig.numel()

    out = torch.empty_like(x_contig)

    def grid(meta):
        return (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)

    _add_kernel[grid](
        x_contig,
        y_contig,
        out,
        n_elements,
    )
    return out
"""

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
