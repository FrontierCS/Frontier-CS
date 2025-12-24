import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=32),
        triton.Config({'BLOCK_SIZE': 32768}, num_warps=32),
        triton.Config({'BLOCK_SIZE': 65536}, num_warps=32),
        triton.Config({'BLOCK_SIZE': 131072}, num_warps=32),
    ],
    key=['n_elements'],
)
@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    \"\"\"
    Triton kernel for element-wise vector addition.
    \"\"\"
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)
    
    # Calculate the offsets for the current block.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Create a mask to handle the last block, which may not be full.
    mask = offsets < n_elements
    
    # Load data from global memory, applying the mask.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Perform the element-wise addition.
    output = x + y
    
    # Store the result back to global memory.
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)
    
    Returns:
        Output tensor of shape (268435456,) with x + y
    \"\"\"
    # Allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)
    
    # Ensure tensors are contiguous for optimal memory access.
    assert x.is_contiguous() and y.is_contiguous() and output.is_contiguous()
    
    n_elements = output.numel()
    
    # Define the grid for the kernel launch.
    # The grid is 1D, and its size is the number of blocks needed to cover all elements.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    add_kernel[grid](
        x,
        y,
        output,
        n_elements,
    )
    
    return output
"""
        return {"code": code}
