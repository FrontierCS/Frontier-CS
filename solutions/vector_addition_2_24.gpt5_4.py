import torch
import triton
import triton.language as tl


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements: tl.constexpr, BLOCK_SIZE: tl.constexpr, UNROLL: tl.constexpr):
    pid = tl.program_id(axis=0)
    base = pid * BLOCK_SIZE * UNROLL
    arange = tl.arange(0, BLOCK_SIZE)
    for u in range(UNROLL):
        idx = base + u * BLOCK_SIZE + arange
        mask = idx < n_elements
        x = tl.load(x_ptr + idx, mask=mask)
        y = tl.load(y_ptr + idx, mask=mask)
        tl.store(out_ptr + idx, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensors")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.numel() == 0:
        return x + y
    if x.device.type != 'cuda' or y.device.type != 'cuda':
        return x + y
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    # Heuristics for large vectors: tune block size and unroll
    if n >= (1 << 23):  # >= 8,388,608
        BLOCK_SIZE = 4096
        UNROLL = 4
        num_warps = 8
        num_stages = 4
    elif n >= (1 << 20):
        BLOCK_SIZE = 2048
        UNROLL = 4
        num_warps = 4
        num_stages = 4
    else:
        BLOCK_SIZE = 1024
        UNROLL = 2
        num_warps = 4
        num_stages = 3

    grid = (triton.cdiv(n, BLOCK_SIZE * UNROLL),)
    _vector_add_kernel[grid](
        x, y, out,
        n_elements=n,
        BLOCK_SIZE=BLOCK_SIZE,
        UNROLL=UNROLL,
        num_warps=num_warps,
        num_stages=num_stages
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements: tl.constexpr, BLOCK_SIZE: tl.constexpr, UNROLL: tl.constexpr):
    pid = tl.program_id(axis=0)
    base = pid * BLOCK_SIZE * UNROLL
    arange = tl.arange(0, BLOCK_SIZE)
    for u in range(UNROLL):
        idx = base + u * BLOCK_SIZE + arange
        mask = idx < n_elements
        x = tl.load(x_ptr + idx, mask=mask)
        y = tl.load(y_ptr + idx, mask=mask)
        tl.store(out_ptr + idx, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensors")
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.numel() == 0:
        return x + y
    if x.device.type != 'cuda' or y.device.type != 'cuda':
        return x + y
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n = x.numel()
    out = torch.empty_like(x)

    # Heuristics tuned for large vectors and NVIDIA L4
    if n >= (1 << 23):  # >= 8,388,608
        BLOCK_SIZE = 4096
        UNROLL = 4
        num_warps = 8
        num_stages = 4
    elif n >= (1 << 20):
        BLOCK_SIZE = 2048
        UNROLL = 4
        num_warps = 4
        num_stages = 4
    else:
        BLOCK_SIZE = 1024
        UNROLL = 2
        num_warps = 4
        num_stages = 3

    grid = (triton.cdiv(n, BLOCK_SIZE * UNROLL),)
    _vector_add_kernel[grid](
        x, y, out,
        n_elements=n,
        BLOCK_SIZE=BLOCK_SIZE,
        UNROLL=UNROLL,
        num_warps=num_warps,
        num_stages=num_stages
    )
    return out
'''
        return {"code": code}
