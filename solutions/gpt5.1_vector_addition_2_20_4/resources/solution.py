import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
                pid = tl.program_id(axis=0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x_vals = tl.load(x_ptr + offsets, mask=mask)
                y_vals = tl.load(y_ptr + offsets, mask=mask)
                out_vals = x_vals + y_vals
                tl.store(out_ptr + offsets, out_vals, mask=mask)


            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                """
                Element-wise addition of two vectors using a Triton kernel.

                Args:
                    x: Input tensor of shape (1048576,)
                    y: Input tensor of shape (1048576,)

                Returns:
                    Output tensor of shape (1048576,) with x + y
                """
                # Fallback to PyTorch if not on CUDA
                if x.device.type != "cuda" or y.device.type != "cuda":
                    return x + y

                assert x.shape == y.shape
                assert x.is_contiguous() and y.is_contiguous()

                n_elements = x.numel()
                out = torch.empty_like(x)

                BLOCK_SIZE = 1024
                grid = ((n_elements + BLOCK_SIZE - 1) // BLOCK_SIZE,)

                _add_kernel[grid](
                    x,
                    y,
                    out,
                    n_elements,
                    BLOCK_SIZE=BLOCK_SIZE,
                    num_warps=4,
                    num_stages=2,
                )

                return out
            """
        )
        return {"code": code}
