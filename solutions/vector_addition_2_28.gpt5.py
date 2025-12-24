import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    z = x + y
    tl.store(out_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)

    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if not x.is_cuda or not y.is_cuda:
        raise ValueError("x and y must be CUDA tensors")
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    # Heuristics for large 1D bandwidth-bound kernel
    # Values chosen to maximize throughput on NVIDIA L4
    BLOCK_SIZE = 4096
    NUM_WARPS = 8
    NUM_STAGES = 3

    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=NUM_WARPS, num_stages=NUM_STAGES)
    return out
'''
        return {"code": code}
