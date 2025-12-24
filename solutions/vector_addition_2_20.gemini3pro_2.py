class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
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
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    # Load inputs
    # Explicitly hinting contiguous access is handled by Triton for simple arithmetic on pointers
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Computation
    output = x + y
    
    # Store output
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using Triton.
    
    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)
    
    Returns:
        Output tensor of shape (1048576,) with x + y
    """
    # Allocate output
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    # Configuration
    # BLOCK_SIZE=1024 is generally optimal for bandwidth-bound element-wise operations
    # on modern GPUs (like L4/Ada) to maximize occupancy and memory coalescing.
    BLOCK_SIZE = 1024
    
    # Grid definition
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    
    # Launch kernel
    add_kernel[grid](
        x, y, output,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4  # Standard warp count sufficient for memory bound ops
    )
    
    return output
"""
        return {"code": code}
