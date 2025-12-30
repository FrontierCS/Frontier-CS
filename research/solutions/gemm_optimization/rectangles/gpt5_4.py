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

            def _configs():
                return [
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 64}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64}, num_stages=3, num_warps=4),
                ]

            @triton.autotune(configs=_configs(), key=['M', 'N', 'K'])
            @triton.jit
            def _matmul_gelu_kernel_fp16(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_remaining = K
                while k_remaining > 0:
                    k_mask_a = offs_k[None, :] < k_remaining
                    k_mask_b = offs_k[:, None] < k_remaining
                    a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_a, other=0.0)
                    b = tl.load(b_ptrs, mask=k_mask_b & (offs_n[None, :] < N), other=0.0)
                    acc += tl.dot(a, b)
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k_remaining -= BLOCK_K

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c = acc.to(tl.float16)
                tl.store(c_ptrs, c, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

            @triton.autotune(configs=_configs(), key=['M', 'N', 'K'])
            @triton.jit
            def _matmul_gelu_kernel_bf16(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_remaining = K
                while k_remaining > 0:
                    k_mask_a = offs_k[None, :] < k_remaining
                    k_mask_b = offs_k[:, None] < k_remaining
                    a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_a, other=0.0).to(tl.bfloat16)
                    b = tl.load(b_ptrs, mask=k_mask_b & (offs_n[None, :] < N), other=0.0).to(tl.bfloat16)
                    acc += tl.dot(a, b)
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k_remaining -= BLOCK_K

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c = acc.to(tl.bfloat16)
                tl.store(c_ptrs, c, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

            @triton.autotune(configs=_configs(), key=['M', 'N', 'K'])
            @triton.jit
            def _matmul_gelu_kernel_fp32(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_remaining = K
                while k_remaining > 0:
                    k_mask_a = offs_k[None, :] < k_remaining
                    k_mask_b = offs_k[:, None] < k_remaining
                    a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_a, other=0.0)
                    b = tl.load(b_ptrs, mask=k_mask_b & (offs_n[None, :] < N), other=0.0)
                    acc += tl.dot(a, b)
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k_remaining -= BLOCK_K

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

            def _launch_kernel(a: torch.Tensor, b: torch.Tensor, c: torch.Tensor):
                M, K = a.shape
                Kb, N = b.shape
                assert K == Kb, "Inner dimensions must match"
                assert a.is_cuda and b.is_cuda and c.is_cuda, "All tensors must be on CUDA device"
                assert a.device == b.device == c.device, "All tensors must be on the same device"

                grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

                if a.dtype == torch.float16:
                    _matmul_gelu_kernel_fp16[grid](
                        a, b, c,
                        M, N, K,
                        a.stride(0), a.stride(1),
                        b.stride(0), b.stride(1),
                        c.stride(0), c.stride(1),
                    )
                elif a.dtype == torch.bfloat16:
                    _matmul_gelu_kernel_bf16[grid](
                        a, b, c,
                        M, N, K,
                        a.stride(0), a.stride(1),
                        b.stride(0), b.stride(1),
                        c.stride(0), c.stride(1),
                    )
                elif a.dtype == torch.float32:
                    _matmul_gelu_kernel_fp32[grid](
                        a, b, c,
                        M, N, K,
                        a.stride(0), a.stride(1),
                        b.stride(0), b.stride(1),
                        c.stride(0), c.stride(1),
                    )
                else:
                    raise TypeError(f"Unsupported dtype: {a.dtype}")

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if not (a.is_cuda and b.is_cuda):
                    raise ValueError("Inputs must be CUDA tensors")
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Inputs must be 2D matrices")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Incompatible matrix shapes")

                # Promote/align dtypes: prefer a's dtype, cast b if needed
                preferred_dtype = a.dtype
                if preferred_dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    # Fallback to float16 for unsupported dtypes
                    preferred_dtype = torch.float16
                    a = a.to(preferred_dtype)
                if b.dtype != preferred_dtype:
                    b = b.to(preferred_dtype)

                M, K = a.shape
                Kb, N = b.shape

                # Allocate output
                c = torch.empty((M, N), device=a.device, dtype=preferred_dtype)

                # Launch specialized Triton kernel
                _launch_kernel(a, b, c)
                return c
        """)
        return {"code": code}