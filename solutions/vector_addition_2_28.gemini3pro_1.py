import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
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
    # Get program ID
    pid = tl.program_id(axis=0)
    
    # Calculate offsets
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Create mask for boundary conditions
    mask = offsets < n_elements
    
    # Load x and y
    # Explicitly hinting cache eviction policy can sometimes help bandwidth, 
    # but for simple streaming add, defaults are usually optimal.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Perform addition
    output = x + y
    
    # Store result
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using Triton.
    Optimized for large vectors and high bandwidth.
    """
    # Create output tensor
    output = torch.empty_like(x)
    
    n_elements = output.numel()
    
    # Block size of 1024 is typically optimal for simple element-wise operations 
    # on modern NVIDIA GPUs to maximize occupancy and memory coalescing.
    BLOCK_SIZE = 1024
    
    # Calculate grid size
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch kernel
    add_kernel[grid](
        x, 
        y, 
        output, 
        n_elements, 
        BLOCK_SIZE=BLOCK_SIZE
    )
    
    return output
"""
        }
