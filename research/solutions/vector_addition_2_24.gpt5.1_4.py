import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    out_ptr,
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
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
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)

    Returns:
        Output tensor of shape (16777216,) with x + y
    """
    if not (x.is_cuda and y.is_cuda):
        raise ValueError("Inputs must be CUDA tensors.")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape.")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same CUDA device.")

    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n_elements = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096

    def grid(meta):
        return (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)

    with torch.cuda.device_of(x):
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
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}