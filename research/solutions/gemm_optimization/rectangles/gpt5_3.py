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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=5),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=5),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def _matmul_gelu_kernel(
                A_ptr, B_ptr, C_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                OUT_DTYPE: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)
                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)
                group_m = GROUP_M
                num_pid_in_group = group_m * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * group_m
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + (pid_in_group % group_m)
                pid_n = pid_in_group // group_m

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_iter = 0
                while k_iter < K:
                    a_mask = (offs_m[:, None] < M) & (k_iter + offs_k[None, :] < K)
                    b_mask = (k_iter + offs_k[:, None] < K) & (offs_n[None, :] < N)
                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                    acc += tl.dot(a, b)
                    k_iter += BLOCK_K
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                c = gelu(acc)

                c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, c.to(OUT_DTYPE), mask=c_mask)

            def _to_triton_dtype(dtype: torch.dtype):
                if dtype == torch.float16:
                    return tl.float16
                if dtype == torch.bfloat16:
                    return tl.bfloat16
                if dtype == torch.float32:
                    return tl.float32
                raise ValueError(f'Unsupported dtype: {dtype}')

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                """
                Matrix multiplication with GELU activation.

                Args:
                    a: Tensor of shape (M, K)
                    b: Tensor of shape (K, N)

                Returns:
                    Tensor of shape (M, N) with GELU applied
                """
                if not (a.is_cuda and b.is_cuda):
                    raise ValueError("Inputs must be CUDA tensors.")
                if a.dim() != 2 or b.dim() != 2:
                    raise ValueError("Inputs must be rank-2 tensors.")
                if a.shape[1] != b.shape[0]:
                    raise ValueError(f"Incompatible shapes: {a.shape} x {b.shape}")

                M, K = a.shape
                Kb, N = b.shape
                assert K == Kb

                # Choose output dtype as input dtype of A (and B should match)
                if a.dtype != b.dtype:
                    # If mixed dtype, promote minimally to float32 for correctness
                    out_dtype = torch.float32
                else:
                    out_dtype = a.dtype
                if out_dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    # Fallback: compute in float32 and return float32
                    out_dtype = torch.float32

                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
                )

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                    OUT_DTYPE=_to_triton_dtype(out_dtype),
                )
                return c
        """)
        return {"code": code}