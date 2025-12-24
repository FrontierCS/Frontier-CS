import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
                pid = tl.program_id(axis=0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                tl.store(out_ptr + offsets, x + y, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                """
                Element-wise addition of two vectors using a Triton kernel.
                Args:
                    x: Input tensor of shape (N,)
                    y: Input tensor of shape (N,)
                Returns:
                    Output tensor of shape (N,) with x + y
                """
                assert x.numel() == y.numel(), "Input sizes must match"
                n_elements = x.numel()
                if n_elements == 0:
                    return torch.empty_like(x)

                # If no GPU is available, fall back to PyTorch (CPU or other device)
                if x.device.type != 'cuda' or y.device.type != 'cuda':
                    return x + y

                # Ensure inputs are contiguous for best performance
                assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"

                out = torch.empty_like(x)

                # Choose a performant configuration for large, bandwidth-bound workloads
                # BLOCK_SIZE of 8192 with 8 warps provides high occupancy and good memory coalescing
                BLOCK_SIZE = 8192
                grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)

                _add_kernel[grid](
                    x, y, out,
                    n_elements,
                    BLOCK_SIZE=BLOCK_SIZE,
                    num_warps=8,
                    num_stages=2,
                )
                return out
        """)
        return {"code": code}
