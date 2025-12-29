import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with a Python code string for a Triton kernel.
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations with varying block sizes
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8, num_stages=2),
        # Configurations with larger block sizes to maximize data per thread block
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16, num_stages=2),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16, num_stages=2),
        # An even larger block size, potentially beneficial for pure memory-bound tasks
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16, num_stages=2),
    ],
    key=['n_elements'],
)
@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    \"\"\"
    Triton kernel for element-wise vector addition.
    This kernel is designed to be memory-bound and leverages Triton's autotuner
    to find the optimal BLOCK_SIZE for maximizing memory bandwidth.
    \"\"\"
    # Each program instance (thread block) computes a chunk of the output vector.
    pid = tl.program_id(axis=0)

    # Calculate the offsets for the elements this program will process.
    # tl.arange creates a compile-time vector: [0, 1, 2, ..., BLOCK_SIZE-1].
    # This is then broadcasted with the program ID to get the global offsets.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to safely handle the last block if the total number of
    # elements is not a multiple of BLOCK_SIZE. This prevents out-of-bounds
    # memory accesses, which is crucial for correctness.
    mask = offsets < n_elements

    # Load a block of data from the input tensors x and y.
    # The loads are masked to ensure we don't read past the end of the tensors.
    # Triton's compiler will coalesce these loads into wide memory transactions.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition. This is a simple arithmetic operation.
    output = x + y

    # Store the result block back to the output tensor.
    # The store is also masked to prevent writing out-of-bounds.
    tl.store(output_ptr + offsets, output, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors using a Triton kernel.
    
    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)
    
    Returns:
        Output tensor of shape (1048576,) with x + y
    \"\"\"
    # Allocate the output tensor. It has the same shape and device as the input.
    output = torch.empty_like(x)
    
    # Get the total number of elements. The problem specifies 2^20.
    n_elements = x.numel()

    # The grid determines the number of program instances to launch.
    # We need enough instances to cover all 'n_elements'.
    # Each instance handles 'BLOCK_SIZE' elements, so we use ceiling division.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the kernel. The autotuner will have selected the best config.
    # The 'meta' object in the grid lambda contains the autotuner's chosen parameters.
    add_kernel[grid](x, y, output, n_elements)
    
    return output
"""
        return {"code": kernel_code}