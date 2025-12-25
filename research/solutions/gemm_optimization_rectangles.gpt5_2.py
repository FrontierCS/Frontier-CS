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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'NUM_STAGES': 4}, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'NUM_STAGES': 4}, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'NUM_STAGES': 4}, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'NUM_STAGES': 4}, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'NUM_STAGES': 4}, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64, 'NUM_STAGES': 3}, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 192, 'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=4),
                    triton.Config({'BLOCK_M': 192, 'BLOCK_N': 64,  'BLOCK_K': 32, 'NUM_STAGES': 3}, num_warps=4),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def matmul_kernel(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                NUM_STAGES: tl.constexpr
            ):
                pid_m = tl.program_id(axis=0)
                pid_n = tl.program_id(axis=1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k0 = 0
                while k0 < K:
                    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + (k0 + offs_k[None, :]) * stride_ak)
                    b_ptrs = b_ptr + ((k0 + offs_k[:, None]) * stride_bk + offs_n[None, :] * stride_bn)

                    a_mask = (offs_m[:, None] < M) & (k0 + offs_k[None, :] < K)
                    b_mask = (offs_n[None, :] < N) & (k0 + offs_k[:, None] < K)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b)

                    k0 += BLOCK_K

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc, mask=c_mask)

            def _is_supported_dtype(dtype: torch.dtype):
                return dtype in (torch.float16, torch.bfloat16, torch.float32)

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("matmul expects 2D tensors")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Incompatible shapes: a: (%d, %d), b: (%d, %d)" % (a.shape[0], a.shape[1], b.shape[0], b.shape[1]))
                if not a.is_cuda or not b.is_cuda:
                    raise ValueError("Inputs must be CUDA tensors")
                if not _is_supported_dtype(a.dtype) or not _is_supported_dtype(b.dtype):
                    raise TypeError("Supported dtypes are float16, bfloat16, and float32")

                M, K = a.shape
                Kb, N = b.shape

                # Choose output dtype: keep input dtype if matching; else promote to float32
                if a.dtype == b.dtype and a.dtype in (torch.float16, torch.bfloat16):
                    out_dtype = a.dtype
                elif a.dtype == b.dtype and a.dtype == torch.float32:
                    out_dtype = torch.float32
                else:
                    out_dtype = torch.float32

                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))

                matmul_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                )
                return c
        """)
        return {"code": code}
