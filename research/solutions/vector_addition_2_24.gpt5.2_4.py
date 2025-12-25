import os
import torch
import triton
import triton.language as tl

N_ELEMENTS: int = 1 << 24
BLOCK_SIZE: int = 8192
NUM_WARPS: int = 8
NUM_STAGES: int = 2


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK + tl.arange(0, BLOCK)

    px = x_ptr + offsets
    py = y_ptr + offsets
    po = out_ptr + offsets

    tl.multiple_of(px, 16)
    tl.multiple_of(py, 16)
    tl.multiple_of(po, 16)
    tl.max_contiguous(px, 128)
    tl.max_contiguous(py, 128)
    tl.max_contiguous(po, 128)

    x = tl.load(px, cache_modifier=".cg", eviction_policy="evict_last").to(tl.float32)
    y = tl.load(py, cache_modifier=".cg", eviction_policy="evict_last").to(tl.float32)
    out = x + y
    tl.store(po, out)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not x.is_cuda or not y.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")
    if x.numel() != N_ELEMENTS or y.numel() != N_ELEMENTS:
        raise ValueError(f"Expected inputs with exactly {N_ELEMENTS} elements")
    if x.dtype != y.dtype:
        raise ValueError("Inputs must have the same dtype")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("Inputs must be contiguous")
    out = torch.empty_like(x)
    grid = (N_ELEMENTS // BLOCK_SIZE,)
    _add_kernel[grid](x, y, out, BLOCK=BLOCK_SIZE, num_warps=NUM_WARPS, num_stages=NUM_STAGES)
    return out


_KERNEL_CODE = f"""import torch
import triton
import triton.language as tl

N_ELEMENTS = 1 << 24
BLOCK_SIZE = {BLOCK_SIZE}
NUM_WARPS = {NUM_WARPS}
NUM_STAGES = {NUM_STAGES}

@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK + tl.arange(0, BLOCK)

    px = x_ptr + offsets
    py = y_ptr + offsets
    po = out_ptr + offsets

    tl.multiple_of(px, 16)
    tl.multiple_of(py, 16)
    tl.multiple_of(po, 16)
    tl.max_contiguous(px, 128)
    tl.max_contiguous(py, 128)
    tl.max_contiguous(po, 128)

    x = tl.load(px, cache_modifier=".cg", eviction_policy="evict_last").to(tl.float32)
    y = tl.load(py, cache_modifier=".cg", eviction_policy="evict_last").to(tl.float32)
    out = x + y
    tl.store(po, out)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not x.is_cuda or not y.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")
    if x.numel() != N_ELEMENTS or y.numel() != N_ELEMENTS:
        raise ValueError(f"Expected inputs with exactly {{N_ELEMENTS}} elements")
    if x.dtype != y.dtype:
        raise ValueError("Inputs must have the same dtype")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("Inputs must be contiguous")
    out = torch.empty_like(x)
    grid = (N_ELEMENTS // BLOCK_SIZE,)
    _add_kernel[grid](x, y, out, BLOCK=BLOCK_SIZE, num_warps=NUM_WARPS, num_stages=NUM_STAGES)
    return out
"""


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}