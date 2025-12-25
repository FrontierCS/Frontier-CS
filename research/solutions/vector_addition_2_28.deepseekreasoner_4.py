import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
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
                pid = tl.program_id(axis=0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                output = x + y
                tl.store(output_ptr + offsets, output, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                n_elements = x.numel()
                output = torch.empty_like(x)
                grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
                add_kernel[grid](x, y, output, n_elements, BLOCK_SIZE=4096)
                return output
        """)
        return {"code": code.strip()}
