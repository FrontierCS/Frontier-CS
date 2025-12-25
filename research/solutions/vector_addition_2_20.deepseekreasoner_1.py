import torch
import triton
import triton.language as tl
import os

@triton.jit
def _add_kernel(x_ptr, y_ptr, output_ptr, n_elements, 
                BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.jit
def _add_kernel_vec4(x_ptr, y_ptr, output_ptr, n_elements,
                     BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    
    x_vec = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y_vec = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    output = x_vec + y_vec
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.jit
def _add_kernel_optimized(x_ptr, y_ptr, output_ptr, n_elements,
                          BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    result = x + y
    tl.store(output_ptr + offsets, result, mask=mask)
    
    # Prefetch next block if possible
    next_offsets = offsets + BLOCK_SIZE * tl.num_programs(axis=0)
    next_mask = next_offsets < n_elements
    if tl.sum(next_mask, axis=0) > 0:
        _ = tl.load(x_ptr + next_offsets, mask=next_mask, eviction_policy='evict_last')
        _ = tl.load(y_ptr + next_offsets, mask=next_mask, eviction_policy='evict_last')

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    # Use the fastest kernel configuration
    if n_elements >= 131072:  # Use optimized kernel for medium/large vectors
        grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
        _add_kernel_optimized[grid](
            x, y, output, n_elements,
            BLOCK_SIZE=1024
        )
    else:  # Fallback for smaller sizes
        grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
        _add_kernel[grid](
            x, y, output, n_elements,
            BLOCK_SIZE=128
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def _add_kernel_optimized(x_ptr, y_ptr, output_ptr, n_elements,
                          BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    result = x + y
    tl.store(output_ptr + offsets, result, mask=mask)
    
    # Prefetch next block if possible
    next_offsets = offsets + BLOCK_SIZE * tl.num_programs(axis=0)
    next_mask = next_offsets < n_elements
    if tl.sum(next_mask, axis=0) > 0:
        _ = tl.load(x_ptr + next_offsets, mask=next_mask, eviction_policy='evict_last')
        _ = tl.load(y_ptr + next_offsets, mask=next_mask, eviction_policy='evict_last')

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    # Optimized configuration for 2^20 elements
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Use optimal block size for NVIDIA L4 (24GB VRAM)
    # 1024 threads per block provides good occupancy and memory coalescing
    _add_kernel_optimized[grid](
        x, y, output, n_elements,
        BLOCK_SIZE=1024
    )
    
    return output'''
        
        return {"code": code}
