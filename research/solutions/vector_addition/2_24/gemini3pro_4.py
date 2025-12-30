import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    # Determine the starting index of the block
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    
    # Generate offsets for the threads in the block
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Create a mask to prevent out-of-bounds access
    mask = offsets < n_elements
    
    # Load data from x and y with masking
    # Triton handles vectorized loads automatically for contiguous data
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Perform element-wise addition
    output = x + y
    
    # Store the result to the output pointer
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    # Ensure inputs are contiguous for maximum memory bandwidth
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
        
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    # Block size of 1024 is generally optimal for element-wise operations on modern GPUs
    # to saturate occupancy and memory bandwidth.
    BLOCK_SIZE = 1024
    
    # Grid size calculation
    grid = lambda meta: ((n_elements + meta['BLOCK_SIZE'] - 1) // meta['BLOCK_SIZE'],)
    
    # Launch the kernel
    # num_warps=4 is standard; increasing to 8 can sometimes help hide latency 
    # but 4 is usually sufficient for simple bandwidth-bound kernels.
    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=BLOCK_SIZE)
    
    return output
"""
        return {"code": code}