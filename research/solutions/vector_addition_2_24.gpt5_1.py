import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def add_kernel(x_ptr, y_ptr, out_ptr, n_elements,
                           BLOCK_SIZE: tl.constexpr,
                           ALIGNED_ELEMS: tl.constexpr):
                pid = tl.program_id(0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                tl.multiple_of(offsets, ALIGNED_ELEMS)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask, other=0)
                y = tl.load(y_ptr + offsets, mask=mask, other=0)
                z = x + y
                tl.store(out_ptr + offsets, z, mask=mask)

            def _pick_meta(n, dtype_bytes):
                # Heuristic tuned for bandwidth-bound workloads
                if dtype_bytes <= 2:
                    block = 16384
                    num_warps = 8
                elif dtype_bytes == 4:
                    block = 8192
                    num_warps = 8
                else:
                    block = 4096
                    num_warps = 4
                return block, num_warps

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                \"""
                Element-wise addition of two vectors.
                
                Args:
                    x: Input tensor of shape (16777216,)
                    y: Input tensor of shape (16777216,)
                
                Returns:
                    Output tensor of shape (16777216,) with x + y
                \"""
                if x.shape != y.shape:
                    raise ValueError("x and y must have the same shape")
                if x.dtype != y.dtype:
                    raise ValueError("x and y must have the same dtype")
                if x.numel() == 0:
                    return x + y
                if x.is_cuda != y.is_cuda:
                    raise ValueError("x and y must be both on CUDA or both on CPU")
                if not x.is_cuda:
                    return x + y

                if x.device != y.device:
                    raise ValueError("x and y must be on the same CUDA device")

                n = x.numel()
                out = torch.empty_like(x)
                dtype_bytes = x.element_size()
                block, num_warps = _pick_meta(n, dtype_bytes)
                grid = (triton.cdiv(n, block),)
                align_elems = max(1, 16 // dtype_bytes)

                # Launch on the correct CUDA device/stream
                with torch.cuda.device_of(x):
                    add_kernel[grid](
                        x, y, out, n,
                        BLOCK_SIZE=block,
                        ALIGNED_ELEMS=align_elems,
                        num_warps=num_warps,
                        num_stages=1,
                    )
                return out
        """)
        return {"code": code}