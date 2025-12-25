import torch
import triton
import triton.language as tl
from typing import Dict, Any

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr,
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

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.shape == y.shape and x.numel() == 1048576, "Inputs must be 1,048,576 elements"
    
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    # Optimal configuration for NVIDIA L4
    # Tuned for 4MB vectors and memory bandwidth
    BLOCK_SIZE = 2048  # Optimized for L4 memory coalescing
    num_warps = 4  # Balance occupancy and instruction-level parallelism
    
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    add_kernel[grid](
        x, y, output, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=num_warps,
    )
    return output

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        kernel_code = """import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr,
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

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda and y.is_cuda, "Inputs must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.shape == y.shape and x.numel() == 1048576, "Inputs must be 1,048,576 elements"
    
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    # Optimal configuration for NVIDIA L4
    BLOCK_SIZE = 2048
    num_warps = 4
    
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    add_kernel[grid](
        x, y, output, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=num_warps,
    )
    return output"""
        
        return {"code": kernel_code}
