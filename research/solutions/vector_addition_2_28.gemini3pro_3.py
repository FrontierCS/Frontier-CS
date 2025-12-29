import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(r"""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def add_kernel(
                x_ptr, 
                y_ptr, 
                output_ptr, 
                n_elements, 
                BLOCK_SIZE: tl.constexpr
            ):
                """
                Triton kernel for element-wise vector addition.
                Optimized for coalesced memory access and maximum bandwidth.
                """
                # Program ID calculation
                pid = tl.program_id(axis=0)
                
                # Calculate offsets for this block
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                
                # Create mask for boundary conditions
                # Even though input size 2^28 is a multiple of BLOCK_SIZE (1024),
                # keeping mask is good practice and has negligible cost.
                mask = offsets < n_elements
                
                # Vectorized Loads
                # Triton handles memory coalescing automatically for contiguous ranges
                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                
                # Computation
                output = x + y
                
                # Vectorized Store
                tl.store(output_ptr + offsets, output, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                """
                Element-wise addition of two vectors using Triton.
                """
                # Allocate output buffer (ensures same device and dtype)
                output = torch.empty_like(x)
                n_elements = x.numel()
                
                # Kernel Configuration
                # BLOCK_SIZE=1024 is typically optimal for element-wise operations 
                # on NVIDIA GPUs to maximize occupancy.
                BLOCK_SIZE = 1024
                
                # num_warps=8 (256 threads) provides sufficient parallelism to hide 
                # global memory latency on high-bandwidth GPUs like L4.
                num_warps = 8
                
                # Grid definition
                grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']), )
                
                # Launch kernel
                add_kernel[grid](
                    x, 
                    y, 
                    output, 
                    n_elements, 
                    BLOCK_SIZE=BLOCK_SIZE, 
                    num_warps=num_warps
                )
                
                return output
        """)
        return {"code": code}