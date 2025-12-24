import torch
import triton
import triton.language as tl
import sys
import inspect


BLOCK_SIZE = 1024
NUM_WARPS = 8
NUM_STAGES = 1


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)

    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("Input tensors must be CUDA tensors")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n_elements = x.numel()
    out = torch.empty_like(x)

    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    _vector_add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=NUM_WARPS,
        num_stages=NUM_STAGES,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if "__file__" in globals():
            return {"program_path": __file__}
        source = inspect.getsource(sys.modules[__name__])
        return {"code": source}
