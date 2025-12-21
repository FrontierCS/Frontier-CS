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

@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    # Each program instance computes a block of BLOCK_SIZE elements.
    pid = tl.program_id(axis=0)

    # Compute the offsets for the current block.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to handle the case where n_elements is not a multiple of BLOCK_SIZE.
    mask = offsets < n_elements

    # Load the input vectors from global memory.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

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
    
    n_elements = x.numel()
    
    # This block size is chosen to be large for good memory bandwidth
    # while ensuring enough blocks are launched to saturate the GPU's SMs.
    # For a vector of 2^20 elements on an L4 GPU (~60 SMs), 16384 gives
    # 64 blocks, which is a reasonable number. Larger block sizes generally
    # yield better performance for memory-bound kernels.
    BLOCK_SIZE = 16384
    
    # Calculate the grid size. The grid is 1D, and its size is the number of
    # blocks needed to cover all elements.
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    
    # Launch the Triton kernel.
    # Using more warps (e.g., 8) can help hide memory latency.
    add_kernel[grid](
        x, 
        y, 
        output, 
        n_elements, 
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8
    )
    
    return output
"""
        return {"code": kernel_code}
