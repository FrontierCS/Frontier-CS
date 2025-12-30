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
        
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        # Configurations with larger block sizes for better memory throughput
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 32768}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 65536}, num_warps=32),
        triton.Config({'BLOCK_SIZE': 131072}, num_warps=32),
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
    '''
    Triton kernel for element-wise vector addition.
    This kernel is optimized for memory bandwidth by processing large, contiguous blocks of data.
    '''
    # Each program instance computes a block of the output vector.
    # The program_id (pid) is the index of the block.
    pid = tl.program_id(axis=0)

    # Calculate the starting offset of the block for this program instance.
    block_start = pid * BLOCK_SIZE
    
    # Create a range of offsets for the elements in the block.
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to prevent out-of-bounds memory access.
    # This is crucial for correctness if n_elements is not a multiple of BLOCK_SIZE.
    # For this specific problem (size=2^20), if BLOCK_SIZE is a power of 2,
    # the mask will be all-true, incurring no runtime overhead.
    mask = offsets < n_elements

    # Load a block of data from x and y tensors.
    # The mask ensures that we only load valid elements.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition.
    output = x + y

    # Store the resulting block back to the output tensor.
    tl.store(output_ptr + offsets, output, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors using a Triton kernel.
    
    Args:
        x: Input tensor of shape (1048576,)
        y: Input tensor of shape (1048576,)
    
    Returns:
        Output tensor of shape (1048576,) with x + y
    """
    # Get the total number of elements from the input tensor.
    n_elements = x.numel()
    
    # Allocate the output tensor. It should be on the same device as the inputs.
    output = torch.empty_like(x)

    # The grid defines the number of program instances to launch.
    # We create a 1D grid where each program instance handles one block of data.
    # The grid size is determined by the total number of elements and the BLOCK_SIZE
    # chosen by the autotuner. We use a lambda to dynamically compute the grid size
    # based on the autotuner's metadata.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the Triton kernel.
    # The autotuner will benchmark the configurations provided in the decorator
    # and automatically select the one with the best performance for the given inputs.
    # The arguments are passed to the kernel function.
    add_kernel[grid](
        x,
        y,
        output,
        n_elements,
        # BLOCK_SIZE is handled by the autotuner and doesn't need to be passed explicitly.
    )
    
    return output

"""
        return {"code": kernel_code}