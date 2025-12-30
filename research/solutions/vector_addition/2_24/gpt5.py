import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Input tensors must be on CUDA"
    assert x.dtype == y.dtype, "Input tensors must have same dtype"
    assert x.is_contiguous() and y.is_contiguous(), "Input tensors must be contiguous"
    assert x.numel() == y.numel(), "Input tensors must have same number of elements"
    n_elements = x.numel()
    out = torch.empty_like(x)
    cc = torch.cuda.get_device_capability(x.device)
    cc_num = cc[0] * 10 + cc[1]
    # Larger blocks reduce scheduling overhead; keep moderate to avoid register pressure.
    if x.dtype in (torch.float16, torch.bfloat16, torch.int16):
        block = 8192 if cc_num >= 80 else 4096
    else:
        block = 8192 if cc_num >= 80 else 4096
    num_warps = 8 if block >= 4096 else 4
    grid = (triton.cdiv(n_elements, block),)
    _add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=block, num_warps=num_warps, num_stages=2)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Input tensors must be on CUDA"
    assert x.dtype == y.dtype, "Input tensors must have same dtype"
    assert x.is_contiguous() and y.is_contiguous(), "Input tensors must be contiguous"
    assert x.numel() == y.numel(), "Input tensors must have same number of elements"
    n_elements = x.numel()
    out = torch.empty_like(x)
    cc = torch.cuda.get_device_capability(x.device)
    cc_num = cc[0] * 10 + cc[1]
    if x.dtype in (torch.float16, torch.bfloat16, torch.int16):
        block = 8192 if cc_num >= 80 else 4096
    else:
        block = 8192 if cc_num >= 80 else 4096
    num_warps = 8 if block >= 4096 else 4
    grid = (triton.cdiv(n_elements, block),)
    _add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=block, num_warps=num_warps, num_stages=2)
    return out
'''
        return {"code": code}