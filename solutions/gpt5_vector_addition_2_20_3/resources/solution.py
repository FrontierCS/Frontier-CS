import os
import sys
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

    tl.multiple_of(block_start, BLOCK_SIZE)
    tl.max_contiguous(offsets, BLOCK_SIZE)

    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(out_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.dim() != 1 or y.dim() != 1:
        x = x.reshape(-1)
        y = y.reshape(-1)

    # Ensure tensors are on CUDA and contiguous
    if not x.is_cuda:
        x = x.to(device="cuda", non_blocking=True)
    if not y.is_cuda:
        y = y.to(device="cuda", non_blocking=True)
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096  # tuned for medium vectors on modern GPUs
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)

    _vec_add_kernel[grid](
        x, y, out,
        n,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=2,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": __file__}
        except NameError:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
