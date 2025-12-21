import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with a Python code string for the vector addition problem.
        """
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 32768}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 65536}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 131072}, num_warps=16),
    ],
    key=['N'],
)
@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    N: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
):
    \"\"\"
    Triton kernel for vector addition.
    This kernel is optimized for memory bandwidth by processing large contiguous blocks of data.
    \"\"\"
    # Each program instance computes a block of BLOCK_SIZE elements.
    # The program ID (pid) determines which block this instance is responsible for.
    pid = tl.program_id(axis=0)

    # Calculate the offsets for the current block.
    # tl.arange(0, BLOCK_SIZE) creates a vector of [0, 1, ..., BLOCK_SIZE-1].
    # This is added to the block's starting offset.
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)

    # Create a mask to guard against out-of-bounds memory accesses.
    # This is crucial if the total number of elements N is not a multiple of BLOCK_SIZE.
    # The mask ensures that we only load and store data within the valid range of the tensors.
    mask = offsets < N

    # Load data from global memory.
    # The mask is applied here to prevent reading beyond the tensor's boundaries.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition.
    output = x + y

    # Store the result back to global memory.
    # The mask is applied again to prevent writing beyond the tensor's boundaries.
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
    # Get the total number of elements in the input tensor.
    N = x.numel()

    # Allocate the output tensor. It should have the same shape, dtype, and device as the input.
    output = torch.empty_like(x)

    # The grid determines the number of kernel instances to launch.
    # We create a 1D grid where each instance handles one block of data.
    # triton.cdiv(N, meta['BLOCK_SIZE']) calculates the ceiling division,
    # ensuring we have enough blocks to cover all N elements.
    # The grid is defined as a lambda to allow the autotuner to inject the
    # BLOCK_SIZE value at runtime.
    grid = lambda meta: (triton.cdiv(N, meta['BLOCK_SIZE']),)

    # Launch the Triton kernel.
    # The autotuner will automatically benchmark the configurations specified in the decorator
    # and choose the one with the best performance for the given input size N.
    add_kernel[grid](x, y, output, N)

    return output
"""
        return {"code": code}
