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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 2}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 2}, num_stages=3, num_warps=8),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def matmul_kernel_fp16(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)
                num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
                num_pid_n = (N + BLOCK_N - 1) // BLOCK_N
                group_size_m = GROUP_M
                group_id = pid // (group_size_m * num_pid_n)
                group_size_m = min(num_pid_m - group_id * group_size_m, group_size_m)
                pid_in_group = pid % (group_size_m * num_pid_n)
                pid_m = group_id * GROUP_M + (pid_in_group % group_size_m)
                pid_n = pid_in_group // group_size_m

                rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                ram = rm[:, None] * stride_am
                rbn = rn[None, :] * stride_bn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k0 = 0
                a_ptrs = a_ptr + ram + (k0 + tl.arange(0, BLOCK_K))[None, :] * stride_ak
                b_ptrs = b_ptr + (k0 + tl.arange(0, BLOCK_K))[:, None] * stride_bk + rbn

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + tl.arange(0, BLOCK_K)
                    a_mask = (rm[:, None] < M) & (k_offsets[None, :] < K)
                    b_mask = (k_offsets[:, None] < K) & (rn[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    a = a.to(tl.float16)
                    b = b.to(tl.float16)

                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + ram + rbn
                c_mask = (rm[:, None] < M) & (rn[None, :] < N)
                tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 2}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 2}, num_stages=3, num_warps=8),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def matmul_kernel_bf16(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)
                num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
                num_pid_n = (N + BLOCK_N - 1) // BLOCK_N
                group_size_m = GROUP_M
                group_id = pid // (group_size_m * num_pid_n)
                group_size_m = min(num_pid_m - group_id * group_size_m, group_size_m)
                pid_in_group = pid % (group_size_m * num_pid_n)
                pid_m = group_id * GROUP_M + (pid_in_group % group_size_m)
                pid_n = pid_in_group // group_size_m

                rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                ram = rm[:, None] * stride_am
                rbn = rn[None, :] * stride_bn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k0 = 0
                a_ptrs = a_ptr + ram + (k0 + tl.arange(0, BLOCK_K))[None, :] * stride_ak
                b_ptrs = b_ptr + (k0 + tl.arange(0, BLOCK_K))[:, None] * stride_bk + rbn

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + tl.arange(0, BLOCK_K)
                    a_mask = (rm[:, None] < M) & (k_offsets[None, :] < K)
                    b_mask = (k_offsets[:, None] < K) & (rn[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    a = a.to(tl.bfloat16)
                    b = b.to(tl.bfloat16)

                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + ram + rbn
                c_mask = (rm[:, None] < M) & (rn[None, :] < N)
                tl.store(c_ptrs, acc.to(tl.bfloat16), mask=c_mask)

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 2}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 2}, num_stages=3, num_warps=8),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def matmul_kernel_fp32(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)
                num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
                num_pid_n = (N + BLOCK_N - 1) // BLOCK_N
                group_size_m = GROUP_M
                group_id = pid // (group_size_m * num_pid_n)
                group_size_m = min(num_pid_m - group_id * group_size_m, group_size_m)
                pid_in_group = pid % (group_size_m * num_pid_n)
                pid_m = group_id * GROUP_M + (pid_in_group % group_size_m)
                pid_n = pid_in_group // group_size_m

                rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                ram = rm[:, None] * stride_am
                rbn = rn[None, :] * stride_bn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k0 = 0
                a_ptrs = a_ptr + ram + (k0 + tl.arange(0, BLOCK_K))[None, :] * stride_ak
                b_ptrs = b_ptr + (k0 + tl.arange(0, BLOCK_K))[:, None] * stride_bk + rbn

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + tl.arange(0, BLOCK_K)
                    a_mask = (rm[:, None] < M) & (k_offsets[None, :] < K)
                    b_mask = (k_offsets[:, None] < K) & (rn[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + ram + rbn
                c_mask = (rm[:, None] < M) & (rn[None, :] < N)
                tl.store(c_ptrs, acc.to(tl.float32), mask=c_mask)

            def _get_grid(M, N, META):
                return ((triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N'])),)

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                assert a.ndim == 2 and b.ndim == 2, "Input tensors must be 2D"
                assert a.shape[1] == b.shape[0], "Incompatible matrix shapes"
                assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"

                M, K = a.shape
                K2, N = b.shape
                dtype = a.dtype
                assert b.dtype == dtype, "Input tensors must have the same dtype"
                out = torch.empty((M, N), device=a.device, dtype=dtype)

                stride_am = a.stride(0)
                stride_ak = a.stride(1)
                stride_bk = b.stride(0)
                stride_bn = b.stride(1)
                stride_cm = out.stride(0)
                stride_cn = out.stride(1)

                if dtype == torch.float16:
                    matmul_kernel_fp16[_get_grid(M, N)](
                        a, b, out,
                        M, N, K,
                        stride_am, stride_ak,
                        stride_bk, stride_bn,
                        stride_cm, stride_cn,
                    )
                elif dtype == torch.bfloat16:
                    matmul_kernel_bf16[_get_grid(M, N)](
                        a, b, out,
                        M, N, K,
                        stride_am, stride_ak,
                        stride_bk, stride_bn,
                        stride_cm, stride_cn,
                    )
                else:
                    matmul_kernel_fp32[_get_grid(M, N)](
                        a, b, out,
                        M, N, K,
                        stride_am, stride_ak,
                        stride_bk, stride_bn,
                        stride_cm, stride_cn,
                    )
                return out
        """).strip("\n")
        return {"code": code}