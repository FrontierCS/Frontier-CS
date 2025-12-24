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
        solution_code = """
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
    This kernel is optimized for memory bandwidth by processing large blocks of data.
    \"\"\"
    # Get the program ID for the current instance.
    pid = tl.program_id(axis=0)

    # Calculate the offsets for the block of elements this program will handle.
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)

    # Create a mask to handle the case where the vector size is not a multiple of BLOCK_SIZE.
    # This prevents out-of-bounds memory access for the last block.
    mask = offsets < n_elements

    # Load a block of data from input tensors x and y.
    # The mask ensures that we only load valid elements.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition.
    result = x + y

    # Store the result back into the output tensor.
    tl.store(output_ptr + offsets, result, mask=mask)


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
    
    # Get the total number of elements.
    n_elements = x.numel()
    
    # Define the grid for launching the kernel.
    # The grid is 1D, and its size is the number of blocks needed to cover all elements.
    # triton.cdiv provides a ceiling division to ensure all elements are processed.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    # The autotuner will automatically select the best BLOCK_SIZE from the configs.
    add_kernel[grid](
        x, 
        y, 
        output, 
        n_elements,
    )
    
    return output
"""
        return {"code": solution_code}
