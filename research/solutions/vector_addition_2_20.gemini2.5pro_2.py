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

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
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
    Triton kernel for vector addition. This kernel is designed for memory-bound
    operations and is optimized by using vector loads and stores. Autotuning is
    used to select the best BLOCK_SIZE and num_warps for the target hardware.
    \"\"\"
    # Each program instance (block) computes a chunk of the output vector.
    # The program_id identifies which block this instance is.
    pid = tl.program_id(axis=0)

    # Calculate memory offsets for the data this block will process.
    # tl.arange(0, BLOCK_SIZE) creates a vector [0, 1, ..., BLOCK_SIZE-1].
    # This, combined with the block start, gives the global offsets.
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)

    # Since N (2^20) is a multiple of all potential BLOCK_SIZEs (powers of 2),
    # boundary checks (masking) are not needed. This simplifies the kernel
    # and can slightly improve performance.
    x = tl.load(x_ptr + offsets)
    y = tl.load(y_ptr + offsets)
    
    # Perform the element-wise addition.
    output = x + y
    
    # Store the result back to global memory.
    tl.store(output_ptr + offsets, output)


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
    
    # The total number of elements in the vector.
    N = x.numel()
    
    # The grid determines how many instances of the kernel to launch.
    # It is a function of the kernel's meta-parameters, which allows the
    # autotuner to adjust the grid size based on the BLOCK_SIZE it's testing.
    grid = lambda meta: (triton.cdiv(N, meta['BLOCK_SIZE']),)
    
    # Launch the kernel. Triton's JIT compiler and autotuner handle the
    # compilation and optimization. The autotuner will benchmark the configs
    # specified in @triton.autotune and cache the best performing one.
    add_kernel[grid](x, y, output, N)
    
    return output
"""
        return {"code": kernel_code}