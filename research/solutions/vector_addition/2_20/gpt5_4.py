import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 2048}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 4096}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 8192}, num_warps=8, num_stages=2),
                ],
                key=['n_elements'],
            )
            @triton.jit
            def _vec_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
                pid = tl.program_id(axis=0)
                block_start = pid * BLOCK_SIZE
                offsets = block_start + tl.arange(0, BLOCK_SIZE)
                mask = offsets < n_elements
                x = tl.load(x_ptr + offsets, mask=mask)
                y = tl.load(y_ptr + offsets, mask=mask)
                tl.store(out_ptr + offsets, x + y, mask=mask)

            def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
                if x.numel() != y.numel():
                    raise ValueError("Input tensors must have the same number of elements.")
                n = x.numel()

                # Ensure on CUDA
                device = x.device if x.is_cuda else (y.device if y.is_cuda else torch.device('cuda'))
                if not x.is_cuda:
                    x = x.to(device, non_blocking=True)
                if not y.is_cuda:
                    y = y.to(device, non_blocking=True)

                # Match dtypes to avoid unnecessary casts; prefer common dtype
                if x.dtype != y.dtype:
                    common_dtype = torch.result_type(x, y)
                    if x.dtype != common_dtype:
                        x = x.to(common_dtype)
                    if y.dtype != common_dtype:
                        y = y.to(common_dtype)
                dtype = x.dtype

                # Ensure contiguity (guaranteed by spec, but keep for safety)
                if not x.is_contiguous():
                    x = x.contiguous()
                if not y.is_contiguous():
                    y = y.contiguous()

                out = torch.empty_like(x, dtype=dtype, device=device)

                grid = lambda META: (triton.cdiv(n, META['BLOCK_SIZE']),)
                _vec_add_kernel[grid](x, y, out, n, num_warps=None, num_stages=None)
                return out
        """)
        return {"code": code}