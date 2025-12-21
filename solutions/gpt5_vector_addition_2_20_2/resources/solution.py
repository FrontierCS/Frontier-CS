import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
                pid = tl.program_id(0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                z = x + y
                tl.store(out_ptr + offsets, z, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                if x.shape != y.shape:
                    raise ValueError("Input tensors must have the same shape")
                if x.dtype != y.dtype:
                    raise ValueError("Input tensors must have the same dtype")
                if not x.is_contiguous() or not y.is_contiguous():
                    x = x.contiguous()
                    y = y.contiguous()

                n_elements = x.numel()
                if x.device.type != "cuda":
                    return x + y

                out = torch.empty_like(x)
                grid = lambda meta: (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)
                add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE=8192, num_warps=8, num_stages=2)
                return out
        """)
        return {"code": code}
