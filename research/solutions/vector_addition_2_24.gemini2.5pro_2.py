import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Using textwrap.dedent to properly handle indentation in the multi-line string.
        # .lstrip() removes any leading newline from the start of the dedented string.
        code = textwrap.dedent("""
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
                
                # Calculate the offsets for the current block.
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                
                # Create a mask to prevent out-of-bounds memory access. This is essential
                # for handling vector sizes that are not perfect multiples of BLOCK_SIZE.
                # For this specific problem (2^24 elements) and a power-of-two BLOCK_SIZE,
                # the mask will be all-true, but it's a robust programming practice.
                mask = offsets < n_elements
                
                # Load inputs from global memory. The 'evict_last' policy hints to the
                # hardware that this data is streaming and should be evicted soon after use,
                # which is optimal for read-once memory access patterns.
                x = tl.load(x_ptr + offsets, mask=mask, eviction_policy="evict_last")
                y = tl.load(y_ptr + offsets, mask=mask, eviction_policy="evict_last")
                
                # Perform the element-wise addition.
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
                n_elements = x.numel()
                
                # Allocate the output tensor. It's crucial to do this on the same device as the inputs.
                output = torch.empty_like(x)
                
                # A large block size is chosen to maximize memory bandwidth.
                # It increases the amount of work per thread block, which helps to hide memory
                # latency and allows the GPU to issue more parallel memory requests.
                # For a large vector of 2^24 elements, a BLOCK_SIZE of 65536 creates 256 blocks,
                # which is sufficient to saturate all Streaming Multiprocessors (SMs) on
                # a modern GPU like the NVIDIA L4.
                BLOCK_SIZE = 65536
                
                # The launch grid is 1D. The size of the grid is the total number of elements
                # divided by the block size, rounded up to ensure all elements are processed.
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
        """).lstrip()
        return {"code": code}