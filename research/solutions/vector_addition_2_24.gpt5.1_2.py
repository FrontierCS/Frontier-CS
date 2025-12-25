import torch
import triton
import triton.language as tl


@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements.")
    if not x.is_cuda or not y.is_cuda:
        raise ValueError("Input tensors must be CUDA tensors.")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device.")

    # Flatten to 1D for simplicity; view is cheap for contiguous tensors
    x_flat = x.contiguous().view(-1)
    y_flat = y.contiguous().view(-1)

    n_elements = x_flat.numel()
    out_flat = torch.empty_like(x_flat)

    BLOCK_SIZE = 4096
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    add_kernel[grid](
        x_flat,
        y_flat,
        out_flat,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4,
        num_stages=2,
    )

    return out_flat.view_as(x)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import os

        with open(os.path.abspath(__file__), "r", encoding="utf-8") as f:
            code = f.read()
        return {"code": code}
