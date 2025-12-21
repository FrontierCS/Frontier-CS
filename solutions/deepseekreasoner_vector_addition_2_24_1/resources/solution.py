import torch
import triton
import triton.language as tl
from typing import Dict, Optional

@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.jit
def add_kernel_tuned(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    NUM_STAGES: tl.constexpr,
    NUM_WARPS: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)
    
    Returns:
        Output tensor of shape (16777216,) with x + y
    """
    assert x.is_cuda and y.is_cuda, "Tensors must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Tensors must be contiguous"
    assert x.shape == y.shape, "Tensors must have same shape"
    assert x.shape[0] == 16777216, f"Expected 2^24 elements, got {x.shape[0]}"
    
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    if n_elements >= 2**24:
        grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
        add_kernel_tuned[grid](
            x, y, output, n_elements,
            BLOCK_SIZE=1024,
            NUM_STAGES=3,
            NUM_WARPS=4
        )
    else:
        BLOCK_SIZE = 1024
        grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
        add_kernel[grid](
            x, y, output, n_elements,
            BLOCK_SIZE=BLOCK_SIZE
        )
    
    return output

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.jit
def add_kernel_tuned(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    NUM_STAGES: tl.constexpr,
    NUM_WARPS: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Tensors must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Tensors must be contiguous"
    assert x.shape == y.shape, "Tensors must have same shape"
    
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    if n_elements >= 2**24:
        grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
        add_kernel_tuned[grid](
            x, y, output, n_elements,
            BLOCK_SIZE=1024,
            NUM_STAGES=3,
            NUM_WARPS=4
        )
    else:
        BLOCK_SIZE = 1024
        grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
        add_kernel[grid](
            x, y, output, n_elements,
            BLOCK_SIZE=BLOCK_SIZE
        )
    
    return output'''
        
        return {"code": code}
