import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.numel() == 0:
        return torch.empty_like(x)
    if x.device.type != "cuda" or y.device.type != "cuda":
        # Fallback to torch for non-GPU tensors (ensures correctness)
        return x + y

    x = x.contiguous()
    y = y.contiguous()
    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    grid = (triton.cdiv(n, BLOCK_SIZE),)

    _vec_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.numel() == 0:
        return torch.empty_like(x)
    if x.device.type != "cuda" or y.device.type != "cuda":
        # Fallback to torch for non-GPU tensors (ensures correctness)
        return x + y

    x = x.contiguous()
    y = y.contiguous()
    n = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 4096
    grid = (triton.cdiv(n, BLOCK_SIZE),)

    _vec_add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
    return out
'''
        return {"code": code}