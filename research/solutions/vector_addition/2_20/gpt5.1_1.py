import torch
import triton
import triton.language as tl
from typing import Dict, Optional


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using a Triton kernel.

    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)

    Returns:
        Tensor of shape (1048576,) with element-wise sum x + y
    """
    if x.shape != y.shape:
        raise ValueError(f"Shape mismatch: x.shape={x.shape}, y.shape={y.shape}")
    if x.device != y.device:
        raise ValueError(f"Device mismatch: x.device={x.device}, y.device={y.device}")

    # Fallback to PyTorch if not on CUDA
    if not x.is_cuda:
        return x + y

    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n_elements = x.numel()
    if n_elements == 0:
        return x + y

    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    _add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4,
    )

    return out


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        """
        Return the path to this module so the evaluator can access the `add` function.
        """
        return {"program_path": __file__}