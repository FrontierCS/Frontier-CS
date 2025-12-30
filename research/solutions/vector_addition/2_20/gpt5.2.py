import os
import torch
import triton
import triton.language as tl

_N = 1 << 20
_BLOCK = 4096


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr, ACCUM_FP32: tl.constexpr, OUT_DTYPE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK
    tl.multiple_of(block_start, 256)
    offsets = block_start + tl.arange(0, BLOCK)

    x = tl.load(x_ptr + offsets, cache_modifier=".cg")
    y = tl.load(y_ptr + offsets, cache_modifier=".cg")

    if ACCUM_FP32:
        z = (x.to(tl.float32) + y.to(tl.float32)).to(OUT_DTYPE)
    else:
        z = x + y

    tl.store(out_ptr + offsets, z, cache_modifier=".cg")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("x and y must be CUDA tensors")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"x and y must have exactly {_N} elements")
    if x.dim() != 1 or y.dim() != 1:
        raise ValueError("x and y must be 1D tensors")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("x and y must be contiguous")

    out = torch.empty_like(x)
    accum_fp32 = x.dtype in (torch.float16, torch.bfloat16)
    if x.dtype == torch.float16:
        out_dtype = tl.float16
    elif x.dtype == torch.bfloat16:
        out_dtype = tl.bfloat16
    elif x.dtype == torch.float32:
        out_dtype = tl.float32
    else:
        raise TypeError(f"Unsupported dtype: {x.dtype}")

    grid = (_N // _BLOCK,)
    _add_kernel[grid](
        x,
        y,
        out,
        BLOCK=_BLOCK,
        ACCUM_FP32=accum_fp32,
        OUT_DTYPE=out_dtype,
        num_warps=8,
        num_stages=4,
    )
    return out


_EMBEDDED_CODE = r'''
import torch
import triton
import triton.language as tl

_N = 1 << 20
_BLOCK = 4096

@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, BLOCK: tl.constexpr, ACCUM_FP32: tl.constexpr, OUT_DTYPE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK
    tl.multiple_of(block_start, 256)
    offsets = block_start + tl.arange(0, BLOCK)
    x = tl.load(x_ptr + offsets, cache_modifier=".cg")
    y = tl.load(y_ptr + offsets, cache_modifier=".cg")
    if ACCUM_FP32:
        z = (x.to(tl.float32) + y.to(tl.float32)).to(OUT_DTYPE)
    else:
        z = x + y
    tl.store(out_ptr + offsets, z, cache_modifier=".cg")

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("x and y must be CUDA tensors")
    if x.dtype != y.dtype:
        raise ValueError("x and y must have the same dtype")
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"x and y must have exactly {_N} elements")
    if x.dim() != 1 or y.dim() != 1:
        raise ValueError("x and y must be 1D tensors")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("x and y must be contiguous")

    out = torch.empty_like(x)
    accum_fp32 = x.dtype in (torch.float16, torch.bfloat16)
    if x.dtype == torch.float16:
        out_dtype = tl.float16
    elif x.dtype == torch.bfloat16:
        out_dtype = tl.bfloat16
    elif x.dtype == torch.float32:
        out_dtype = tl.float32
    else:
        raise TypeError(f"Unsupported dtype: {x.dtype}")

    grid = (_N // _BLOCK,)
    _add_kernel[grid](x, y, out, BLOCK=_BLOCK, ACCUM_FP32=accum_fp32, OUT_DTYPE=out_dtype, num_warps=8, num_stages=4)
    return out
'''.lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        path = globals().get("__file__", None)
        if path and os.path.exists(path):
            return {"program_path": path}
        return {"code": _EMBEDDED_CODE}