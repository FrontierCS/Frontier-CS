import triton
import triton.language as tl
import torch


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
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
    ],
    key=['n_elements'],
)
@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    z_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)
    
    # Calculate offsets for the current block.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Create a mask to handle the last block if n_elements is not a multiple of BLOCK_SIZE.
    # For this problem, n_elements=2^20 is a multiple of all BLOCK_SIZEs, so the mask is always true.
    mask = offsets < n_elements
    
    # Load data from global memory, applying the mask to prevent out-of-bounds access.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Perform element-wise addition.
    output = x + y
    
    # Store the result back to global memory.
    tl.store(z_ptr + offsets, output, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)
    
    Returns:
        Output tensor of shape (1048576,) with x + y
    \"\"\"
    n_elements = x.numel()
    
    # Allocate the output tensor.
    z = torch.empty_like(x)
    
    # The grid is 1D, with a size equal to the number of blocks.
    # The autotuner will determine the best BLOCK_SIZE.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    add_kernel[grid](
        x,
        y,
        z,
        n_elements,
        # BLOCK_SIZE is a template meta-parameter managed by the autotuner
    )
    
    return z

"""
        return {"code": code}
