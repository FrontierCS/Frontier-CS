import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Python code for the Triton kernel.
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Define a range of configurations for the autotuner.
        # BLOCK_SIZE is the most critical parameter for this memory-bound problem.
        # A larger BLOCK_SIZE increases memory coalescing and bandwidth utilization.
        # The num_warps is chosen based on typical hardware limits and block sizes.
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
        triton.Config({'BLOCK_SIZE': 262144}, num_warps=16),
    ],
    key=['n_elements'],  # The key for caching the best configuration.
)
@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    z_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    \"\"\"
    Triton JIT kernel for element-wise vector addition.
    \"\"\"
    # Each program instance (thread block) is responsible for a chunk of the data.
    pid = tl.program_id(axis=0)

    # Calculate the starting offset for the current block.
    block_start = pid * BLOCK_SIZE
    # Create a range of offsets for the elements this block will process.
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Create a mask to prevent out-of-bounds memory access. This is crucial for
    # handling vector sizes that are not a perfect multiple of BLOCK_SIZE.
    mask = offsets < n_elements

    # Load data from global memory into registers.
    # The mask ensures that we only load valid data.
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)

    # Perform the element-wise addition.
    output = x + y

    # Store the result back to global memory.
    tl.store(z_ptr + offsets, output, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Element-wise addition of two vectors using a custom Triton kernel.
    
    This function acts as the launcher for the `add_kernel`. It sets up
    the grid and allocates the output tensor.

    Args:
        x: Input tensor of shape (268435456,). Guaranteed to be contiguous.
        y: Input tensor of shape (268435456,). Guaranteed to be contiguous.
    
    Returns:
        Output tensor of shape (268435456,) with the result of x + y.
    \"\"\"
    # The total number of elements in the vectors.
    n_elements = x.numel()
    
    # Allocate the output tensor. It will have the same shape, dtype, and device
    # as the input tensor `x`.
    z = torch.empty_like(x)
    
    # Define the grid for the kernel launch. The grid size is the number of
    # program instances we want to launch.
    # This is a lambda function because the autotuner needs to be able to
    # calculate the grid size for each configuration it tries.
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch the kernel. The autotuner will handle selecting the best
    # configuration from the list defined in the decorator.
    add_kernel[grid](x, y, z, n_elements)
    
    return z
"""
        return {"code": kernel_code}