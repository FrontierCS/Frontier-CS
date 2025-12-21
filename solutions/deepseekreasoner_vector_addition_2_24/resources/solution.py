import torch
import triton
import triton.language as tl
import math

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    USE_VECTORIZED: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    
    if USE_VECTORIZED:
        # Vectorized loads for better memory bandwidth utilization
        vector_size = 4
        for i in range(0, BLOCK_SIZE, vector_size):
            offsets = block_start + i + tl.arange(0, vector_size)
            mask = offsets < n_elements
            
            x_vec = tl.load(x_ptr + offsets, mask=mask)
            y_vec = tl.load(y_ptr + offsets, mask=mask)
            output_vec = x_vec + y_vec
            tl.store(output_ptr + offsets, output_vec, mask=mask)
    else:
        # Standard scalar approach
        offsets = block_start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < n_elements
        
        x = tl.load(x_ptr + offsets, mask=mask)
        y = tl.load(y_ptr + offsets, mask=mask)
        output = x + y
        tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    # Use optimal block size based on vector length
    # 256-1024 works well for large vectors on L4 GPU
    BLOCK_SIZE = 1024
    
    # Calculate grid size
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Try vectorized version first, fall back to scalar if needed
    try:
        add_kernel[grid](
            x, y, output,
            n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            USE_VECTORIZED=1,
            num_warps=4
        )
    except Exception:
        # Fallback to non-vectorized version
        add_kernel[grid](
            x, y, output,
            n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            USE_VECTORIZED=0,
            num_warps=4
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    USE_VECTORIZED: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    
    if USE_VECTORIZED:
        vector_size = 4
        for i in range(0, BLOCK_SIZE, vector_size):
            offsets = block_start + i + tl.arange(0, vector_size)
            mask = offsets < n_elements
            
            x_vec = tl.load(x_ptr + offsets, mask=mask)
            y_vec = tl.load(y_ptr + offsets, mask=mask)
            output_vec = x_vec + y_vec
            tl.store(output_ptr + offsets, output_vec, mask=mask)
    else:
        offsets = block_start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < n_elements
        
        x = tl.load(x_ptr + offsets, mask=mask)
        y = tl.load(y_ptr + offsets, mask=mask)
        output = x + y
        tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    BLOCK_SIZE = 1024
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    try:
        add_kernel[grid](
            x, y, output,
            n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            USE_VECTORIZED=1,
            num_warps=4
        )
    except Exception:
        add_kernel[grid](
            x, y, output,
            n_elements,
            BLOCK_SIZE=BLOCK_SIZE,
            USE_VECTORIZED=0,
            num_warps=4
        )
    
    return output
"""
        return {"code": code}
