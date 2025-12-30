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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 8},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32,  'GROUP_M': 8},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 8},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32,  'GROUP_M': 8},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32,  'GROUP_M': 8},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64,  'GROUP_M': 8},  num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64,  'GROUP_M': 8},  num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64,  'GROUP_M': 8},  num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64,  'GROUP_M': 8},  num_warps=8, num_stages=3),
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
                ALLOW_TF32: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr,
            ):
                pid = tl.program_id(0)
                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)
                num_pid_in_group = GROUP_M * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * GROUP_M
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + (pid_in_group % GROUP_M)
                pid_n = pid_in_group // GROUP_M

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_remaining = K
                a_mask_m = offs_m[:, None] < M
                b_mask_n = offs_n[None, :] < N

                while k_remaining > 0:
                    k_mask = offs_k[None, :] < k_remaining
                    a = tl.load(a_ptrs, mask=a_mask_m & k_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=k_mask.T & b_mask_n, other=0.0)
                    acc += tl.dot(a, b, allow_tf32=ALLOW_TF32)
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k_remaining -= BLOCK_K

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = a_mask_m & b_mask_n
                tl.store(c_ptrs, acc, mask=c_mask)

            def _is_supported_dtype(dtype):
                return dtype in (torch.float16, torch.bfloat16, torch.float32)

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                assert a.ndim == 2 and b.ndim == 2, "a and b must be 2D tensors"
                assert a.shape[1] == b.shape[0], "Incompatible matrix shapes"
                assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
                assert _is_supported_dtype(a.dtype) and _is_supported_dtype(b.dtype), "Unsupported dtype"
                assert a.dtype == b.dtype, "a and b must have same dtype"

                M, K = a.shape
                Kb, N = b.shape
                dtype = a.dtype
                device = a.device

                # Output dtype matches inputs
                c = torch.empty((M, N), device=device, dtype=dtype)

                def grid(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

                ALLOW_TF32 = True if dtype == torch.float32 else False

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                    ALLOW_TF32=ALLOW_TF32,
                )

                return c
        """)
        return {"code": code}