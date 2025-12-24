import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < n_elements
    x = tl.load(x_ptr + offs, mask=mask)
    y = tl.load(y_ptr + offs, mask=mask)
    tl.store(out_ptr + offs, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")
    if not x.is_cuda:
        return x + y
    n = x.numel()
    out = torch.empty_like(x)
    if n >= 1 << 20:
        block = 4096
        warps = 8
    elif n >= 1 << 18:
        block = 2048
        warps = 4
    else:
        block = 1024
        warps = 4
    grid = (triton.cdiv(n, block),)
    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=block, num_warps=warps, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        src = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < n_elements
    x = tl.load(x_ptr + offs, mask=mask)
    y = tl.load(y_ptr + offs, mask=mask)
    tl.store(out_ptr + offs, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")
    if not x.is_cuda:
        return x + y
    n = x.numel()
    out = torch.empty_like(x)
    if n >= 1 << 20:
        block = 4096
        warps = 8
    elif n >= 1 << 18:
        block = 2048
        warps = 4
    else:
        block = 1024
        warps = 4
    grid = (triton.cdiv(n, block),)
    _add_kernel[grid](x, y, out, n, BLOCK_SIZE=block, num_warps=warps, num_stages=2)
    return out
'''
        return {"code": src}
