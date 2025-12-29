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
        # A range of block sizes to find the optimal configuration for memory bandwidth.
        # Larger block sizes tend to be better for memory-bound kernels on large inputs.
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 32768}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 65536}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 131072}, num_warps=16),
    ],
    # The key tells the autotuner to cache the best config for a given problem size.
    # Since the size is fixed, this will run once and then use the best config.
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
    # Each program instance computes a block of the output vector.
    # The program ID (pid) is the index of the block.
    pid = tl.program_id(axis=0)

    # Calculate the memory offsets for the block this program will process.
    # tl.arange creates a compile-time constant range of offsets.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Since the problem size (2^24) and all tested BLOCK_SIZEs are powers of two,
    # we know that n_elements is always perfectly divisible by BLOCK_SIZE.
    # This allows us to skip boundary checks (masking), which simplifies the
    # generated code and can slightly improve performance.
    
    # Load a block of data from x and y vectors.
    x = tl.load(x_ptr + offsets)
    y = tl.load(y_ptr + offsets)

    # Perform the element-wise addition.
    output = x + y

    # Store the result block back to global memory.
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
    # The problem statement guarantees a specific vector size.
    n_elements = 16777216
    
    # Allocate the output tensor.
    output = torch.empty((n_elements,), device=x.device, dtype=x.dtype)
    
    # The grid launch function determines the number of program instances (blocks) to launch.
    # It is a function of the BLOCK_SIZE chosen by the autotuner.
    # triton.cdiv ensures we have enough blocks to cover all elements.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    # The autotuner will try all configs on the first run and select the fastest one.
    add_kernel[grid](x, y, output, n_elements)
    
    return output
"""
        return {"code": code}