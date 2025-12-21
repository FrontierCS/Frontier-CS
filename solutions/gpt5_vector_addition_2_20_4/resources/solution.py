from typing import Dict

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, N, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < N
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(out_ptr + offsets, z, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)
    
    Returns:
        Output tensor of shape (1048576,) with x + y
    """
    if x.device.type != 'cuda' or y.device.type != 'cuda':
        # Fallback for CPU tensors; GPU performance evaluation will pass CUDA tensors.
        return x + y
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.numel() == y.numel(), "Input sizes must match"
    assert x.dtype == y.dtype, "Input dtypes must match"
    N = x.numel()
    BLOCK_SIZE = 4096  # tuned for 2^20 elems on L4; 256 programs -> good occupancy
    grid = (triton.cdiv(N, BLOCK_SIZE),)
    if x.dtype != torch.float32:
        x_fp32 = x.to(torch.float32)
        y_fp32 = y.to(torch.float32)
        out_fp32 = torch.empty_like(x_fp32)
        _add_kernel[grid](x_fp32, y_fp32, out_fp32, N, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
        return out_fp32.to(dtype=x.dtype)
    else:
        out = torch.empty_like(x)
        _add_kernel[grid](x, y, out, N, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
        return out
'''
        return {"code": code}
