import os
import torch

try:
    import triton
    import triton.language as tl
except Exception:  # pragma: no cover
    triton = None
    tl = None

_N = 1 << 24


if triton is not None:

    @triton.jit
    def _add_kernel(x_ptr, y_ptr, z_ptr, BLOCK: tl.constexpr):
        pid = tl.program_id(axis=0)
        base = pid * BLOCK

        x_blk = x_ptr + base
        y_blk = y_ptr + base
        z_blk = z_ptr + base

        tl.multiple_of(x_blk, 16)
        tl.multiple_of(y_blk, 16)
        tl.multiple_of(z_blk, 16)

        offs = tl.arange(0, BLOCK)
        x = tl.load(x_blk + offs, cache_modifier=".cg", eviction_policy="evict_first")
        y = tl.load(y_blk + offs, cache_modifier=".cg", eviction_policy="evict_first")
        tl.store(z_blk + offs, x + y, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensors")
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"Input tensors must have exactly {_N} elements")
    if x.device != y.device:
        raise ValueError("x and y must be on the same device")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.dim() != 1 or y.dim() != 1:
        raise ValueError("x and y must be 1D tensors")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    if triton is None or (not x.is_cuda):
        return x + y

    out = torch.empty_like(x)
    BLOCK = 1024
    grid = (_N // BLOCK,)
    _add_kernel[grid](x, y, out, BLOCK=BLOCK, num_warps=8, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    return {"code": f.read()}
        except Exception:
            pass
        return {"code": ""}