import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(r"""
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr, 
    y_ptr, 
    output_ptr, 
    n_elements, 
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    # Load data
    # Loading contiguous data with offsets is automatically coalesced
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Compute
    output = x + y
    
    # Store result
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using Triton.
    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)
    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    # Pre-allocate output tensor
    output = torch.empty_like(x)
    n_elements = x.numel()
    
    # Configuration
    # BLOCK_SIZE=1024 is a robust choice for vector addition, ensuring 
    # aligned memory access and sufficient occupancy.
    BLOCK_SIZE = 1024
    
    # Grid definition
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Kernel launch
    add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=BLOCK_SIZE)
    
    return output
""")
        return {"code": code}
