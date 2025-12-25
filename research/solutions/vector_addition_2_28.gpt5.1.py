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

                # Alignment and contiguity hints for better codegen
                tl.multiple_of(offsets, BLOCK_SIZE)
                tl.max_contiguous(offsets, BLOCK_SIZE)

                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                tl.store(out_ptr + offsets, x + y, mask=mask)


            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                \"\"\"
                Element-wise addition of two vectors.

                Args:
                    x: Input tensor of shape (268435456,)
                    y: Input tensor of shape (268435456,)

                Returns:
                    Output tensor of shape (268435456,) with x + y
                \"\"\"
                if x.shape != y.shape:
                    raise ValueError("Input tensors must have the same shape")
                if x.device != y.device:
                    raise ValueError("Input tensors must be on the same device")

                # CPU fallback (used only if CUDA is unavailable)
                if x.device.type == "cpu":
                    return x + y

                if x.device.type != "cuda":
                    raise ValueError("Only CUDA tensors are supported")

                # Inputs are documented to be contiguous; handle non-contiguous defensively
                if not x.is_contiguous() or not y.is_contiguous():
                    x = x.contiguous()
                    y = y.contiguous()

                n_elements = x.numel()
                out = torch.empty_like(x)

                BLOCK_SIZE = 4096
                grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

                _add_kernel[grid](
                    x, y, out, n_elements,
                    BLOCK_SIZE=BLOCK_SIZE,
                    num_warps=8,
                    num_stages=4,
                )
                return out
            """
        )
        return {"code": code}
