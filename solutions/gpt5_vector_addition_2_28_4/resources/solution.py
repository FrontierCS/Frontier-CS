import os
from textwrap import dedent

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, *,
                                BLOCK_SIZE: tl.constexpr,
                                USE_CG: tl.constexpr):
                pid = tl.program_id(axis=0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                if USE_CG:
                    x = tl.load(x_ptr + offsets, mask=mask, other=0, cache_modifier=".cg")
                    y = tl.load(y_ptr + offsets, mask=mask, other=0, cache_modifier=".cg")
                else:
                    x = tl.load(x_ptr + offsets, mask=mask, other=0)
                    y = tl.load(y_ptr + offsets, mask=mask, other=0)
                tl.store(out_ptr + offsets, x + y, mask=mask)

            def _select_launch_params(dtype, n_elements):
                # Heuristic: for very large streaming ops, 1024 elements/program with 8 warps works well.
                # Ensure BLOCK_SIZE divides the large N=2^28 perfectly to avoid tail masks.
                BLOCK_SIZE = 1024
                num_warps = 8
                num_stages = 1
                use_cg = True
                return BLOCK_SIZE, num_warps, num_stages, use_cg

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                if x.numel() != y.numel():
                    raise ValueError("Input tensors must have the same number of elements")
                if x.device != y.device:
                    raise ValueError("Input tensors must be on the same device")
                if not x.is_contiguous() or not y.is_contiguous():
                    raise ValueError("Input tensors must be contiguous")
                if not x.is_cuda:
                    raise RuntimeError("This function requires CUDA tensors")

                n = x.numel()
                out = torch.empty_like(x)
                BLOCK_SIZE, num_warps, num_stages, use_cg = _select_launch_params(x.dtype, n)
                grid = (triton.cdiv(n, BLOCK_SIZE),)
                _vec_add_kernel[grid](
                    x, y, out, n,
                    BLOCK_SIZE=BLOCK_SIZE,
                    USE_CG=use_cg,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )
                return out
        """)
        return {"code": code}
