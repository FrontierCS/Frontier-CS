import os
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel_masked(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    tl.multiple_of(offsets, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


@triton.jit
def _add_kernel_nomask(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    tl.multiple_of(offsets, BLOCK_SIZE)
    x = tl.load(x_ptr + offsets)
    y = tl.load(y_ptr + offsets)
    out = x + y
    tl.store(out_ptr + offsets, out)


def _select_block_size(n_elements: int) -> int:
    # Simple heuristic: larger blocks for very large vectors
    if n_elements >= (1 << 26):  # 67,108,864
        return 4096
    elif n_elements >= (1 << 22):  # 4,194,304
        return 2048
    else:
        return 1024


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using a Triton kernel.
    """
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")
    if not x.is_cuda:
        raise ValueError("Input tensors must be CUDA tensors")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if not x.is_contiguous() or not y.is_contiguous():
        raise ValueError("Input tensors must be contiguous")
    if x.dtype != y.dtype:
        raise ValueError("Input tensors must have the same dtype")
    if x.dtype != torch.float32:
        raise TypeError("This implementation currently supports only torch.float32")

    n_elements = x.numel()
    if n_elements == 0:
        return x + y

    out = torch.empty_like(x)

    block_size = _select_block_size(n_elements)
    grid = (triton.cdiv(n_elements, block_size),)

    if n_elements % block_size == 0:
        _add_kernel_nomask[grid](
            x,
            y,
            out,
            n_elements,
            BLOCK_SIZE=block_size,
            num_warps=8,
            num_stages=2,
        )
    else:
        _add_kernel_masked[grid](
            x,
            y,
            out,
            n_elements,
            BLOCK_SIZE=block_size,
            num_warps=8,
            num_stages=2,
        )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Return the current file as the kernel implementation.
        """
        return {"program_path": os.path.abspath(__file__)}
