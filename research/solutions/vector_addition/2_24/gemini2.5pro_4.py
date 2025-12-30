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
    BLOCK_SIZE: tl.constexpr,
):
    \"\"\"
    Triton kernel for element-wise vector addition.
    This kernel is optimized for large vectors where the size is a multiple
    of the block size. It uses unmasked loads and stores for maximum efficiency.
    \"\"\"
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)

    # Calculate the memory offsets for the block this program will process.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Load the data from global memory.
    # Since the vector size (2^24) is guaranteed to be a multiple of our
    # chosen power-of-two BLOCK_SIZE, we can perform unmasked loads,
    # which avoids branching and improves performance.
    x = tl.load(x_ptr + offsets)
    y = tl.load(y_ptr + offsets)

    # Perform the element-wise addition.
    # This is the compute part of the kernel, which is minimal for this problem.
    output = x + y

    # Store the result block back to global memory.
    # Similarly, we use an unmasked store.
    tl.store(output_ptr + offsets, output)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (16777216,)
        y: Input tensor of shape (16777216,)
    
    Returns:
        Output tensor of shape (16777216,) with x + y
    \"\"\"
    # The size of the vector is fixed at 2^24 as per the problem specification.
    n_elements = 16777216
    
    # Pre-allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)

    # For memory-bound operations like vector addition, performance is
    # dominated by memory bandwidth. A key optimization is to maximize
    # the amount of contiguous data processed by each GPU core. This is
    # achieved by using a large BLOCK_SIZE.
    # We choose 131072 (2^17), which is a large power-of-two that works well
    # for saturating the memory bus on modern GPUs.
    BLOCK_SIZE = 131072
    
    # Calculate the grid size. The grid determines how many instances of the
    # kernel are launched. It's the total number of elements divided by the
    # number of elements per block (BLOCK_SIZE).
    grid_size = triton.cdiv(n_elements, BLOCK_SIZE)

    # Launch the Triton kernel.
    # The grid is specified as a 1D tuple.
    # `num_warps` is a hint to the compiler about how to schedule the code.
    # For large block sizes, more warps can help hide memory latency.
    add_kernel[(grid_size,)](
        x,
        y,
        output,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=16,
    )

    return output
"""
        return {"code": code}