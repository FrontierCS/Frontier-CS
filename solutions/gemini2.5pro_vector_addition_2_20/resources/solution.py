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
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
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
    # Get the program ID, which corresponds to the block of data this instance will process.
    pid = tl.program_id(axis=0)

    # Calculate the offsets for the elements this program will handle.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to prevent out-of-bounds memory accesses.
    # This is essential for cases where the total number of elements
    # is not a multiple of BLOCK_SIZE.
    mask = offsets < n_elements

    # Load the input data from global memory.
    # The 'evict_last' policy is a hint to the compiler that the loaded data
    # will be used only once and can be evicted from the L1 cache,
    # which can improve performance for streaming operations.
    x = tl.load(x_ptr + offsets, mask=mask, eviction_policy="evict_last")
    y = tl.load(y_ptr + offsets, mask=mask, eviction_policy="evict_last")

    # Perform the element-wise addition.
    output = x + y

    # Store the result back to global memory.
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
    # Allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)
    
    # Ensure all tensors are contiguous in memory for optimal performance.
    assert x.is_contiguous() and y.is_contiguous() and output.is_contiguous()
    
    n_elements = x.numel()
    
    # Define the grid for launching the kernel.
    # The grid is 1D, and the size is the number of blocks needed to cover all elements.
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
        return {"code": kernel_code}
