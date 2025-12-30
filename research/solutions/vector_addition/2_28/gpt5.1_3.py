import os
from typing import Dict, Optional

import torch
import triton
import triton.language as tl


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
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)

    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    if not (x.is_cuda and y.is_cuda):
        return x + y

    assert x.shape == y.shape, "Input tensors must have the same shape"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"

    out = torch.empty_like(x)
    n_elements = x.numel()
    if n_elements == 0:
        return out

    BLOCK_SIZE = 1024

    grid = lambda META: (triton.cdiv(n_elements, META["BLOCK_SIZE"]),)

    _add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=4,
    )

    return out


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"program_path": os.path.abspath(__file__)}