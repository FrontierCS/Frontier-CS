import torch

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
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
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
    \"\"\"
    # Each program instance computes a block of the output.
    # The pid is the unique identifier for each instance.
    pid = tl.program_id(axis=0)

    # Compute the offsets for the current block.
    # Each program processes `BLOCK_SIZE` elements.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to handle the last block if `n_elements` is not a multiple of `BLOCK_SIZE`.
    # This is essential for correctness with arbitrary vector sizes.
    mask = offsets < n_elements

    # Load the input vectors `x` and `y` from global memory.
    # The mask ensures we don't read out of bounds.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition.
    output = x + y

    # Store the result back to global memory.
    # The mask ensures we don't write out of bounds.
    tl.store(output_ptr + offsets, output, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)
    
    Returns:
        Output tensor of shape (16777216,) with x + y
    \"\"\"
    # Allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)
    
    # Get the total number of elements.
    n_elements = x.numel()

    # The grid size is the number of program instances to launch.
    # We need to cover all `n_elements`, so we use `triton.cdiv` (ceiling division).
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    add_kernel[grid](x, y, output, n_elements)
    
    return output
"""
        return {"code": kernel_code}
