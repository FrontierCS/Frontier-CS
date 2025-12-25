import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
                pid = tl.program_id(axis=0)
                offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask, other=0)
                y = tl.load(y_ptr + offsets, mask=mask, other=0)
                z = x + y
                tl.store(out_ptr + offsets, z, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                if not (x.is_cuda and y.is_cuda):
                    return x + y
                assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
                assert x.shape == y.shape, "Input shapes must match"
                assert x.dtype == y.dtype, "Input dtypes must match"

                n_elements = x.numel()
                out = torch.empty_like(x)

                BLOCK_SIZE = 4096
                num_warps = 8
                num_stages = 4

                grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
                add_kernel[grid](
                    x, y, out, n_elements,
                    BLOCK_SIZE=BLOCK_SIZE,
                    num_warps=num_warps,
                    num_stages=num_stages
                )
                return out
        """)
        return {"code": code}
