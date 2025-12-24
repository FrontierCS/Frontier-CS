import os
import torch
import triton
import triton.language as tl


@triton.jit
def _vadd_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not isinstance(x, torch.Tensor) or not isinstance(y, torch.Tensor):
        raise TypeError("x and y must be torch.Tensors")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")
    if x.device.type != "cuda":
        return x + y

    x = x.contiguous()
    y = y.contiguous()
    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 8192
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _vadd_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=4)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": os.path.abspath(__file__)}
        except Exception:
            # Fallback: provide code as a string (self-contained module)
            code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _vadd_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not isinstance(x, torch.Tensor) or not isinstance(y, torch.Tensor):
        raise TypeError("x and y must be torch.Tensors")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")
    if x.device.type != "cuda":
        return x + y

    x = x.contiguous()
    y = y.contiguous()
    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 8192
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    _vadd_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=4)
    return out
"""
            return {"code": code}
