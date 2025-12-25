import os
import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError(f"Shape mismatch: x.shape={x.shape}, y.shape={y.shape}")
    if x.device != y.device:
        raise ValueError(f"Device mismatch: x.device={x.device}, y.device={y.device}")
    if not x.is_cuda:
        # Fallback to PyTorch on CPU
        return x + y

    n_elements = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096

    grid = lambda meta: (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)

    _vec_add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
