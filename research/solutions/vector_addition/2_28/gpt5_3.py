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
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                z = x + y
                tl.store(out_ptr + offsets, z, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                if not (x.is_cuda and y.is_cuda):
                    return x + y
                assert x.is_contiguous() and y.is_contiguous()
                assert x.shape == y.shape
                assert x.dtype == y.dtype
                n = x.numel()
                out = torch.empty_like(x)
                BLOCK_SIZE = 8192
                grid = lambda meta: (triton.cdiv(n, meta['BLOCK_SIZE']),)
                add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE, num_warps=8, num_stages=2)
                return out
        """)
        return {"code": code}