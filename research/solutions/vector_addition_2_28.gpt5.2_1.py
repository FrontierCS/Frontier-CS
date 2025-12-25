import os
import torch
import triton
import triton.language as tl

N_ELEMS = 1 << 28

# Tuned for NVIDIA L4 (memory-bandwidth bound)
BLOCK_SIZE = 4096
NUM_WARPS = 8
NUM_STAGES = 4


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(axis=0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)

    x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
    y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_first")
    tl.store(out_ptr + offs, x + y)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != N_ELEMS or y.numel() != N_ELEMS:
        raise ValueError(f"Expected tensors with exactly {N_ELEMS} elements")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    out = torch.empty_like(x)

    grid = (N_ELEMS // BLOCK_SIZE,)
    _add_kernel[grid](x, y, out, BLOCK=BLOCK_SIZE, num_warps=NUM_WARPS, num_stages=NUM_STAGES)

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}