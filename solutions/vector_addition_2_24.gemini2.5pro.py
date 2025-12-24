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
        return {"code": """import torch
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
    # Each program instance computes a block of the output.
    pid = tl.program_id(axis=0)

    # Calculate memory offsets for the block of data this program instance will handle.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to prevent out-of-bounds memory accesses. This is essential
    # for the last block if n_elements is not a multiple of BLOCK_SIZE.
    mask = offsets < n_elements

    # Load data from global memory (DRAM) to SRAM.
    # The loads are masked to ensure we only read valid data.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition.
    output = x + y

    # Store the result from SRAM back to global memory.
    # The store is also masked to prevent out-of-bounds writes.
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
    # Allocate the output tensor on the same device as the inputs.
    output = torch.empty_like(x)
    
    # Check that the number of elements is as specified.
    n_elements = x.numel()
    assert n_elements == 16777216

    # For a memory-bound kernel on large vectors, a large block size is optimal
    # to maximize memory bandwidth utilization. A larger block size allows each
    # streaming multiprocessor (SM) to process a larger contiguous chunk of memory,
    # which helps hide memory latency and saturate the memory bus.
    # 2^18 = 262144 is chosen as an aggressive but effective size for modern GPUs.
    # For N=2^24, this results in (2^24 / 2^18) = 2^6 = 64 blocks, a good number
    # to keep all SMs on a GPU like the L4 busy.
    BLOCK_SIZE = 262144
    
    # Calculate the grid size. The grid is 1D and has a size equal to the
    # number of blocks needed to cover all elements.
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    # Launch the Triton kernel.
    add_kernel[grid](
        x,
        y,
        output,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
    )
    
    return output
"""}
