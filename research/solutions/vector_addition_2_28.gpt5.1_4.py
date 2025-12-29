import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _add_kernel(
                x_ptr,
                y_ptr,
                out_ptr,
                n_elements: tl.int32,
                BLOCK_SIZE: tl.constexpr,
                HAS_REMAINDER: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                if HAS_REMAINDER:
                    mask = offsets < n_elements
                    x = tl.load(x_ptr + offsets, mask=mask)
                    y = tl.load(y_ptr + offsets, mask=mask)
                    out = x + y
                    tl.store(out_ptr + offsets, out, mask=mask)
                else:
                    x = tl.load(x_ptr + offsets)
                    y = tl.load(y_ptr + offsets)
                    out = x + y
                    tl.store(out_ptr + offsets, out)


            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                """
                Element-wise addition of two vectors.

                Args:
                    x: Input tensor of shape (268435456,)
                    y: Input tensor of shape (268435456,)

                Returns:
                    Output tensor of shape (268435456,) with x + y
                """
                if x.device.type != "cuda" or y.device.type != "cuda":
                    raise ValueError("Input tensors must be CUDA tensors.")
                if x.shape != y.shape:
                    raise ValueError("Input tensors must have the same shape.")
                if not x.is_contiguous():
                    x = x.contiguous()
                if not y.is_contiguous():
                    y = y.contiguous()

                n_elements = x.numel()
                out = torch.empty_like(x)

                BLOCK_SIZE = 4096  # power-of-two, divides 2**28 exactly
                has_remainder = (n_elements % BLOCK_SIZE) != 0
                grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

                _add_kernel[grid](
                    x,
                    y,
                    out,
                    n_elements,
                    BLOCK_SIZE=BLOCK_SIZE,
                    HAS_REMAINDER=has_remainder,
                    num_warps=8,
                    num_stages=2,
                )
                return out
            '''
        )
        return {"code": code}