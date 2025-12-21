import torch
import triton
import triton.language as tl

TRITON_BLOCK_SIZE = 4096
TRITON_NUM_WARPS = 8
TRITON_NUM_STAGES = 4


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("Input tensors must be on CUDA device")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n_elements = x.numel()
    out = torch.empty_like(x)

    grid = lambda meta: (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)

    _add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=TRITON_BLOCK_SIZE,
        num_warps=TRITON_NUM_WARPS,
        num_stages=TRITON_NUM_STAGES,
    )
    return out


KERNEL_CODE = '''
import torch
import triton
import triton.language as tl

TRITON_BLOCK_SIZE = 4096
TRITON_NUM_WARPS = 8
TRITON_NUM_STAGES = 4


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != "cuda" or y.device.type != "cuda":
        raise ValueError("Input tensors must be on CUDA device")
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()

    n_elements = x.numel()
    out = torch.empty_like(x)

    grid = lambda meta: (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)

    _add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=TRITON_BLOCK_SIZE,
        num_warps=TRITON_NUM_WARPS,
        num_stages=TRITON_NUM_STAGES,
    )
    return out
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
