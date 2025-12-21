import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 32768}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 65536}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 131072}, num_warps=16),
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
    Each program instance processes a block of BLOCK_SIZE elements.
    \"\"\"
    # Get the program ID for this instance, which corresponds to the block index
    pid = tl.program_id(axis=0)
    
    # Calculate the starting offset for this block
    block_start = pid * BLOCK_SIZE
    
    # Create a range of offsets for the elements in this block
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Create a mask to handle the case where n_elements is not a multiple of BLOCK_SIZE
    # This prevents out-of-bounds memory accesses in the last block
    mask = offsets < n_elements
    
    # Load BLOCK_SIZE elements from x and y tensors
    # The mask ensures that we only load valid data
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Perform the element-wise addition
    output = x + y
    
    # Store the result back to the output tensor
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)
    
    Returns:
        Output tensor of shape (1048576,) with x + y
    \"\"\"
    # The size of the vector is fixed as per the problem description.
    n_elements = 1048576
    
    # Allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)
    
    # Define the grid for the kernel launch.
    # The grid size is the number of blocks needed to cover all elements.
    # We use a lambda function to dynamically set the grid size based on the
    # BLOCK_SIZE chosen by the autotuner.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    add_kernel[grid](
        x,
        y,
        output,
        n_elements,
        # BLOCK_SIZE is a template meta-parameter and is handled by the autotuner.
    )
    
    return output
"""
        return {"code": code}
