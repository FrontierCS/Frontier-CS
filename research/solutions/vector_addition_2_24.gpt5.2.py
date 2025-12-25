import os
import sys
import inspect
import torch
import triton
import triton.language as tl

N_ELEMENTS = 1 << 24


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr, NUM_ITERS: tl.constexpr):
    pid = tl.program_id(0)
    start = pid * BLOCK * NUM_ITERS
    r = tl.arange(0, BLOCK)
    tl.multiple_of(r, 16)
    tl.max_contiguous(r, 256)
    for i in tl.static_range(0, NUM_ITERS):
        offs = start + i * BLOCK + r
        x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
        y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
        tl.store(out_ptr + offs, x + y, cache_modifier=".cg", eviction_policy="evict_first")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not x.is_cuda or not y.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")
    if x.numel() != N_ELEMENTS or y.numel() != N_ELEMENTS:
        raise ValueError(f"Inputs must have exactly {N_ELEMENTS} elements")
    if x.dtype != y.dtype:
        raise ValueError("Inputs must have the same dtype")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()
    out = torch.empty_like(x)

    BLOCK = 1024
    NUM_ITERS = 4
    grid = (N_ELEMENTS // (BLOCK * NUM_ITERS),)

    _add_kernel[grid](
        x, y, out,
        BLOCK=BLOCK,
        NUM_ITERS=NUM_ITERS,
        num_warps=8,
        num_stages=4,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            p = __file__
            if p and os.path.exists(p):
                return {"program_path": p}
        except Exception:
            pass
        try:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
        except Exception:
            return {"code": ""}