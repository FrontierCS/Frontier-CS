import torch
import triton
import triton.language as tl
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict containing the Python code for the Triton kernel.
        """
        kernel_code = textwrap.dedent("""
        import torch
        import triton
        import triton.language as tl

        @triton.autotune(
            configs=[
                # Basic powers of 2 for block size
                triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
                triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
                triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
                triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
                triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
                # Larger block sizes for high-end GPUs
                triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
                triton.Config({'BLOCK_SIZE': 8192}, num_warps=16),
                triton.Config({'BLOCK_SIZE': 16384}, num_warps=16),
                triton.Config({'BLOCK_SIZE': 32768}, num_warps=16),
                # Max block size that tl.arange can handle, with varying warps
                triton.Config({'BLOCK_SIZE': 65536}, num_warps=16),
                triton.Config({'BLOCK_SIZE': 65536}, num_warps=32),
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
            \"\"\"
            # Get the program ID for this instance
            pid = tl.program_id(axis=0)

            # Calculate the offsets for the block this program will handle
            block_start = pid * BLOCK_SIZE
            offsets = block_start + tl.arange(0, BLOCK_SIZE)

            # Create a mask to prevent out-of-bounds memory access
            mask = offsets < n_elements

            # Load the data from input tensors
            # mask=mask ensures that we don't read beyond the end of the tensors
            x = tl.load(x_ptr + offsets, mask=mask)
            y = tl.load(y_ptr + offsets, mask=mask)

            # Perform the element-wise addition
            output = x + y

            # Store the result back to the output tensor
            # mask=mask ensures that we don't write beyond the end of the tensor
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
            # Allocate the output tensor
            output = torch.empty_like(x)
            
            # Ensure tensors are contiguous for optimal performance
            assert x.is_contiguous() and y.is_contiguous() and output.is_contiguous()
            
            n_elements = output.numel()
            
            # Define the grid for launching the kernel
            # The grid is 1D and has a size equal to the number of blocks needed
            grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
            
            # Launch the kernel
            # The autotuner will automatically select the best BLOCK_SIZE and num_warps
            add_kernel[grid](x, y, output, n_elements)
            
            return output
        """)
        
        return {"code": kernel_code}
