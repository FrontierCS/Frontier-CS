import os
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


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
        raise ValueError(f"Shapes of x {x.shape} and y {y.shape} must match.")
    n_elements = x.numel()
    if n_elements == 0:
        return x + y

    # CPU fallback for robustness; Triton is used on CUDA tensors
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y

    x_ = x.contiguous()
    y_ = y.contiguous()
    out = torch.empty_like(x_)

    BLOCK_SIZE = 4096
    grid = lambda meta: (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)

    _add_kernel[grid](
        x_,
        y_,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=4,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"program_path": os.path.abspath(__file__)}
