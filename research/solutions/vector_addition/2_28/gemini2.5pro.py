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
        triton.Config({'BLOCK_SIZE': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_SIZE': 8192}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_SIZE': 16384}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_SIZE': 32768}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_SIZE': 65536}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_SIZE': 131072}, num_stages=2, num_warps=4),
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
    This kernel is memory-bound. Performance is maximized by using large block sizes
    to increase the amount of work per launch and improve memory access patterns.
    \"\"\"
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)
    
    # Calculate the offsets for the current block. This is a vector operation.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    # Create a mask to prevent out-of-bounds memory accesses for the last block.
    mask = offsets < n_elements
    
    # Load contiguous blocks of data from global memory.
    # The mask ensures that we only load valid elements.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    
    # Perform the element-wise addition.
    output = x + y
    
    # Store the result block back to global memory.
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)
    
    Returns:
        Output tensor of shape (268435456,) with x + y
    \"\"\"
    n_elements = x.numel()
    
    # Allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)
    
    # The grid is 1D, with size equal to the number of blocks.
    # triton.cdiv is a ceiling division utility.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    # The autotuner will select the best BLOCK_SIZE from the configs.
    add_kernel[grid](
        x,
        y,
        output,
        n_elements,
    )
    
    return output
"""
        return {"code": code}