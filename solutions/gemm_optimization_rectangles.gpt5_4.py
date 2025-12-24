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
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64,  'GROUP_M': 4}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256,'BLOCK_K': 64,  'GROUP_M': 4}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128,'BLOCK_K': 64,  'GROUP_M': 8}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64,  'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128,'BLOCK_K': 64,  'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64, 'BLOCK_K': 64,  'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 64,  'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128,'BLOCK_K': 64,  'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32, 'BLOCK_K': 64,  'GROUP_M': 4}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 256,'BLOCK_K': 64,  'GROUP_M': 4}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128,'BLOCK_K': 32,  'GROUP_M': 4}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128,'BLOCK_K': 128, 'GROUP_M': 4}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256,'BLOCK_K': 128, 'GROUP_M': 4}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 128, 'GROUP_M': 4}, num_warps=8, num_stages=2),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def _matmul_gelu_kernel(
                A, B, C,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)

                grid_m = tl.cdiv(M, BLOCK_M)
                grid_n = tl.cdiv(N, BLOCK_N)

                group_size = GROUP_M
                num_pid_m = grid_m
                num_pid_n = grid_n
                group_size = group_size * num_pid_n

                group_id = pid // group_size
                first_pid_m = group_id * GROUP_M
                pid_in_group = pid % group_size
                pid_m = first_pid_m + pid_in_group // num_pid_n
                pid_n = pid_in_group % num_pid_n

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k = 0
                while k < K:
                    a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (k + offs_k[None, :] < K), other=0.0)
                    b = tl.load(b_ptrs, mask=(k + offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)
                    acc += tl.dot(a, b)
                    k += BLOCK_K
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = C + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("a and b must be 2D tensors")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Incompatible shapes: a is (%d, %d), b is (%d, %d)" % (a.shape[0], a.shape[1], b.shape[0], b.shape[1]))
                if not a.is_cuda or not b.is_cuda:
                    raise ValueError("Inputs must be CUDA tensors")
                M, K = a.shape
                Kb, N = b.shape
                assert K == Kb

                # Choose compute dtype: prefer fp16/bf16 for performance
                # Convert at runtime if necessary; output dtype is the torch.result_type of a and b.
                out_dtype = torch.result_type(a.dtype, b.dtype)
                compute_cast = None
                if a.dtype in (torch.float16, torch.bfloat16) and b.dtype == a.dtype:
                    a_comp = a
                    b_comp = b
                else:
                    # Cast to fp16 for compute if not already
                    # This ensures tl.dot uses tensor core friendly types
                    compute_cast = torch.float16
                    a_comp = a.to(compute_cast)
                    b_comp = b.to(compute_cast)

                # Allocate output
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                # Strides
                stride_am, stride_ak = a_comp.stride()
                stride_bk, stride_bn = b_comp.stride()
                stride_cm, stride_cn = c.stride()

                def grid(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

                _matmul_gelu_kernel[grid](
                    a_comp, b_comp, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                )

                return c
        """)
        return {"code": code}
