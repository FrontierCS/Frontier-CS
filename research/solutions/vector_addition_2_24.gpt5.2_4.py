import os
import torch
import triton
import triton.language as tl

N_ELEMENTS = 1 << 24


@triton.jit
def _add_kernel(x_ptr, y_ptr, o_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    x_ptrs = x_ptr + offs
    y_ptrs = y_ptr + offs
    o_ptrs = o_ptr + offs

    tl.multiple_of(offs, 16)
    tl.max_contiguous(offs, 128)
    tl.multiple_of(x_ptrs, 16)
    tl.multiple_of(y_ptrs, 16)
    tl.multiple_of(o_ptrs, 16)

    x = tl.load(x_ptrs, cache_modifier=".cg", eviction_policy="evict_first")
    y = tl.load(y_ptrs, cache_modifier=".cg", eviction_policy="evict_first")
    tl.store(o_ptrs, x + y, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if not (x.is_cuda and y.is_cuda):
        raise ValueError("x and y must be CUDA tensors")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.numel() != N_ELEMENTS or y.numel() != N_ELEMENTS:
        raise ValueError(f"x and y must have exactly {N_ELEMENTS} elements")
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
    if x.dim() != 1:
        x = x.view(-1)
    if y.dim() != 1:
        y = y.view(-1)

    if x.dtype in (torch.float16, torch.bfloat16):
        block = 4096
        num_warps = 8
        num_stages = 4
    elif x.dtype == torch.float32:
        block = 2048
        num_warps = 8
        num_stages = 4
    else:
        block = 1024
        num_warps = 4
        num_stages = 3

    out = torch.empty_like(x)
    grid = (N_ELEMENTS // block,)
    _add_kernel[grid](x, y, out, BLOCK=block, num_warps=num_warps, num_stages=num_stages)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.realpath(__file__)
            with open(path, "r", encoding="utf-8") as f:
                return {"code": f.read()}
        except Exception:
            return {"program_path": os.path.realpath(__file__)}