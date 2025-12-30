import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr, n_elements: tl.constexpr, BLOCK_SIZE: tl.constexpr
):
    program_id = tl.program_id(0)
    
    # Compute the offsets for this block
    block_start = program_id * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Load data from x and y with masking
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    
    # Compute the sum
    z = x + y
    
    # Store the result
    tl.store(output_ptr + offsets, z, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    # Ensure inputs are on GPU and contiguous
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.shape == y.shape and x.shape[0] == 1048576, "Expected shape (1048576,)"
    assert x.dtype == torch.float32 and y.dtype == torch.float32, "Expected float32"
    
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    # Optimal block size for L4 GPU (balances occupancy and memory throughput)
    BLOCK_SIZE = 2048
    
    # Compute grid size
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch kernel
    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=BLOCK_SIZE)
    
    return output
"""
        return {"code": code}