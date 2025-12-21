import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 192, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 192, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _matmul_gelu_kernel(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_SIZE_M: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)
                grid_m = tl.cdiv(M, BLOCK_M)
                grid_n = tl.cdiv(N, BLOCK_N)

                group_id = pid // (GROUP_SIZE_M * grid_n)
                first_pid_m = group_id * GROUP_SIZE_M
                pid_in_group = pid % (GROUP_SIZE_M * grid_n)
                pid_m = first_pid_m + (pid_in_group % GROUP_SIZE_M)
                pid_n = pid_in_group // GROUP_SIZE_M

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                tl.multiple_of(offs_m, BLOCK_M)
                tl.multiple_of(offs_n, BLOCK_N)
                tl.multiple_of(offs_k, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k = 0
                while k < K:
                    a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)
                    b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)
                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                    acc += tl.dot(a, b)
                    k += BLOCK_K
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc, mask=c_mask)

            def _promote_dtype(a: torch.dtype, b: torch.dtype) -> torch.dtype:
                # Simple promotion tailored for float16/bfloat16/float32
                if a == b:
                    return a
                if a == torch.float32 or b == torch.float32:
                    return torch.float32
                if a == torch.bfloat16 or b == torch.bfloat16:
                    # Prefer bfloat16 over float16 to keep wider exponent
                    return torch.bfloat16
                return torch.float16

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("a and b must be 2D tensors")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Incompatible shapes for matmul")
                if not a.is_cuda or not b.is_cuda:
                    raise ValueError("Input tensors must be CUDA tensors")
                M, K = a.shape
                Kb, N = b.shape
                out_dtype = _promote_dtype(a.dtype, b.dtype)
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                )
                return c
        """)
        return {"code": code}
