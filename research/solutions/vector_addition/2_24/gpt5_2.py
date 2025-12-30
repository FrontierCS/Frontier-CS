import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8, num_stages=1),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=8, num_stages=1),
    ],
    key=['N'],
)
@triton.jit
def _add_kernel(X_ptr, Y_ptr, Z_ptr, N, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < N

    x = tl.load(X_ptr + offs, mask=mask)
    y = tl.load(Y_ptr + offs, mask=mask)
    z = x + y
    tl.store(Z_ptr + offs, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)

    Returns:
        Output tensor of shape (16777216,) with x + y
    """
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.dim() != 1:
        raise ValueError("Input tensors must be 1D")
    if x.numel() == 0:
        return x.clone()

    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")

    # CPU fallback for completeness
    if not x.is_cuda:
        return x + y

    x = x.contiguous()
    y = y.contiguous()
    n_elements = x.numel()

    z = torch.empty_like(x)

    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    _add_kernel[grid](x, y, z, n_elements)

    return z


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}