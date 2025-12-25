import os
import sys
import torch
import triton
import triton.language as tl

_N = 1 << 20
_BLOCK = 4096


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr):
    pid = tl.program_id(0)
    base = pid * _BLOCK

    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(out_ptr, 16)
    tl.multiple_of(base, 16)

    offs = base + tl.arange(0, _BLOCK)
    tl.max_contiguous(offs, _BLOCK)

    x = tl.load(x_ptr + offs, cache_modifier="cg")
    y = tl.load(y_ptr + offs, cache_modifier="cg")
    tl.store(out_ptr + offs, x + y)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != _N or y.numel() != _N:
        raise ValueError(f"Expected 1D tensors of exactly {_N} elements")
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("Inputs must be CUDA tensors")
    if x.dtype != y.dtype:
        raise ValueError("Input dtypes must match")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("Inputs must be contiguous")

    out = torch.empty_like(x)
    grid = (_N // _BLOCK,)
    _add_kernel[grid](x, y, out, num_warps=8, num_stages=1)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except Exception:
            pass

        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n"
            "_N = 1 << 20\n"
            "_BLOCK = 4096\n"
            "@triton.jit\n"
            "def _add_kernel(x_ptr, y_ptr, out_ptr):\n"
            "    pid = tl.program_id(0)\n"
            "    base = pid * _BLOCK\n"
            "    tl.multiple_of(x_ptr, 16)\n"
            "    tl.multiple_of(y_ptr, 16)\n"
            "    tl.multiple_of(out_ptr, 16)\n"
            "    tl.multiple_of(base, 16)\n"
            "    offs = base + tl.arange(0, _BLOCK)\n"
            "    tl.max_contiguous(offs, _BLOCK)\n"
            "    x = tl.load(x_ptr + offs, cache_modifier='cg')\n"
            "    y = tl.load(y_ptr + offs, cache_modifier='cg')\n"
            "    tl.store(out_ptr + offs, x + y)\n"
            "def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:\n"
            "    if x.numel() != _N or y.numel() != _N:\n"
            "        raise ValueError(f'Expected 1D tensors of exactly {_N} elements')\n"
            "    if x.device.type != 'cuda' or y.device.type != 'cuda':\n"
            "        raise ValueError('Inputs must be CUDA tensors')\n"
            "    if x.dtype != y.dtype:\n"
            "        raise ValueError('Input dtypes must match')\n"
            "    if not x.is_contiguous() or not y.is_contiguous():\n"
            "        raise ValueError('Inputs must be contiguous')\n"
            "    out = torch.empty_like(x)\n"
            "    grid = (_N // _BLOCK,)\n"
            "    _add_kernel[grid](x, y, out, num_warps=8, num_stages=1)\n"
            "    return out\n"
        )
        return {"code": code}