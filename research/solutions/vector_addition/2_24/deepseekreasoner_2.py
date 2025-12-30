import torch
import triton
import triton.language as tl
import math
from typing import Optional

@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VEC_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    
    # Calculate starting offsets with vectorization
    block_start = pid * BLOCK_SIZE * VEC_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)[:, None] * VEC_SIZE + tl.arange(0, VEC_SIZE)[None, :]
    offsets = tl.view(offsets, -1)
    
    # Create mask for boundary elements
    mask = offsets < n_elements
    
    # Load vectors with vectorization for better memory coalescing
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    
    # Compute addition
    output = x + y
    
    # Store result
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors optimized for large sizes.
    
    Args:
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)
    
    Returns:
        Output tensor of shape (16777216,) with x + y
    """
    # Input validation
    assert x.shape == y.shape, "Input tensors must have same shape"
    assert x.is_cuda and y.is_cuda, "Input tensors must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Input tensors must be contiguous"
    
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    # Optimal configuration for L4 GPU and 2^24 elements
    # Using vectorization for better memory bandwidth utilization
    BLOCK_SIZE = 256  # Good balance between occupancy and register usage
    VEC_SIZE = 4      # Process 4 elements per thread for better coalescing
    
    # Calculate grid size
    elements_per_block = BLOCK_SIZE * VEC_SIZE
    grid_size = triton.cdiv(n_elements, elements_per_block)
    
    # Launch kernel with optimal configuration
    _add_kernel[grid_size](
        x, y, output, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        VEC_SIZE=VEC_SIZE,
        num_warps=8,  # 256 threads / 32 = 8 warps
        num_stages=3,  # Good for memory-bound kernels
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the implementation code.
        """
        code = """import torch
import triton
import triton.language as tl
import math
from typing import Optional

@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VEC_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    
    # Calculate starting offsets with vectorization
    block_start = pid * BLOCK_SIZE * VEC_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)[:, None] * VEC_SIZE + tl.arange(0, VEC_SIZE)[None, :]
    offsets = tl.view(offsets, -1)
    
    # Create mask for boundary elements
    mask = offsets < n_elements
    
    # Load vectors with vectorization for better memory coalescing
    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    
    # Compute addition
    output = x + y
    
    # Store result
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors optimized for large sizes.
    
    Args:
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)
    
    Returns:
        Output tensor of shape (16777216,) with x + y
    \"\"\"
    # Input validation
    assert x.shape == y.shape, "Input tensors must have same shape"
    assert x.is_cuda and y.is_cuda, "Input tensors must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Input tensors must be contiguous"
    
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    # Optimal configuration for L4 GPU and 2^24 elements
    # Using vectorization for better memory bandwidth utilization
    BLOCK_SIZE = 256  # Good balance between occupancy and register usage
    VEC_SIZE = 4      # Process 4 elements per thread for better coalescing
    
    # Calculate grid size
    elements_per_block = BLOCK_SIZE * VEC_SIZE
    grid_size = triton.cdiv(n_elements, elements_per_block)
    
    # Launch kernel with optimal configuration
    _add_kernel[grid_size](
        x, y, output, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        VEC_SIZE=VEC_SIZE,
        num_warps=8,  # 256 threads / 32 = 8 warps
        num_stages=3,  # Good for memory-bound kernels
    )
    
    return output
"""
        return {"code": code}