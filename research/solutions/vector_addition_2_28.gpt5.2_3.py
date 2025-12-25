import sys
import pathlib
import inspect
import torch
import triton
import triton.language as tl

_FIXED_N = 268435456


@triton.jit
def _add_kernel_nomask(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    base = pid * BLOCK
    offs = base + tl.arange(0, BLOCK)

    tl.multiple_of(base, 256)
    tl.multiple_of(offs, 16)
    tl.max_contiguous(offs, 256)

    x = tl.load(x_ptr + offs, cache_modifier=".cg")
    y = tl.load(y_ptr + offs, cache_modifier=".cg")
    tl.store(out_ptr + offs, x + y)


@triton.jit
def _add_kernel_masked(x_ptr, y_ptr, out_ptr, n_elements, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    base = pid * BLOCK
    offs = base + tl.arange(0, BLOCK)
    mask = offs < n_elements

    tl.multiple_of(base, 256)
    tl.multiple_of(offs, 16)
    tl.max_contiguous(offs, 256)

    x = tl.load(x_ptr + offs, mask=mask, other=0, cache_modifier=".cg")
    y = tl.load(y_ptr + offs, mask=mask, other=0, cache_modifier=".cg")
    tl.store(out_ptr + offs, x + y, mask=mask)


def _pick_config(dtype: torch.dtype):
    if dtype in (torch.float16, torch.bfloat16):
        return 8192, 8, 2
    if dtype == torch.float32:
        return 4096, 8, 2
    if dtype == torch.float64:
        return 2048, 8, 2
    return 4096, 8, 2


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.device.type != "cuda" or y.device.type != "cuda":
        return x + y
    if x.dtype != y.dtype:
        raise TypeError("x and y must have the same dtype")
    if x.numel() != y.numel():
        raise ValueError("x and y must have the same number of elements")
    if not x.is_contiguous() or not y.is_contiguous():
        x = x.contiguous()
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    BLOCK, num_warps, num_stages = _pick_config(x.dtype)
    if n == _FIXED_N and (n % BLOCK == 0):
        grid = (n // BLOCK,)
        _add_kernel_nomask[grid](x, y, out, BLOCK=BLOCK, num_warps=num_warps, num_stages=num_stages)
    else:
        grid = (triton.cdiv(n, BLOCK),)
        _add_kernel_masked[grid](x, y, out, n, BLOCK=BLOCK, num_warps=num_warps, num_stages=num_stages)

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            p = pathlib.Path(__file__).resolve()
            return {"program_path": str(p)}
        except Exception:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}