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
    This kernel is designed to be memory-bound and aims to maximize bandwidth.
    \"\"\"
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)

    # Compute the offsets for the current block. tl.arange provides a vectorized
    # range, which is essential for efficient memory access.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to prevent out-of-bounds memory accesses, which is crucial
    # for handling input sizes that are not a multiple of BLOCK_SIZE.
    mask = offsets < n_elements

    # Load a block of data from global memory into registers.
    # The mask ensures we only access valid memory locations.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition. This computation happens on-chip.
    output = x + y

    # Store the result from registers back to global memory.
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
    # Allocate the output tensor. Using torch.empty_like is efficient as it avoids
    # the overhead of initializing memory, which is unnecessary here.
    output = torch.empty_like(x)
    n_elements = output.numel()

    # Define the block size. This is a key tuning parameter for performance.
    # For memory-bound operations on large vectors, a larger block size is
    # generally better as it increases the amount of work per thread block,
    # helping to saturate the GPU's memory bandwidth. 131072 (2^17) is a large
    # power-of-two value that performs well on modern GPUs for this problem scale.
    BLOCK_SIZE = 131072

    # Define the launch grid. The grid is 1D, and its size is the number of
    # blocks needed to cover all elements. triton.cdiv ensures ceiling division.
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    # Launch the Triton kernel. The grid configuration is passed in brackets.
    # PyTorch tensors can be passed directly to the kernel.
    add_kernel[grid](
        x,
        y,
        output,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
    )

    return output
"""
        return {"code": code}
