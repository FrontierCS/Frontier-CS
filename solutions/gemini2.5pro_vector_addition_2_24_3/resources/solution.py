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
        code = """import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 32768}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 65536}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 131072}, num_warps=16),
    ],
    key=['n_elements'],
)
@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)

    # Calculate memory offsets for this instance.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to handle the last block, which may be smaller.
    mask = offsets < n_elements

    # Load data from global memory.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the addition.
    output = x + y

    # Store the result back to global memory.
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
    # Pre-allocate the output tensor.
    output = torch.empty_like(x)
    n_elements = output.numel()

    # The grid defines how many instances of the kernel are launched.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the kernel.
    _add_kernel[grid](
        x,
        y,
        output,
        n_elements,
    )
    
    return output
"""
        return {"code": code}
