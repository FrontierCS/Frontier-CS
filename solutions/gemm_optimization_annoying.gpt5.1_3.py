import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=3, num_warps=2),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _matmul_gelu_kernel(
                A, B, C,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                **META,
            ):
                BLOCK_M: tl.constexpr = META['BLOCK_M']
                BLOCK_N: tl.constexpr = META['BLOCK_N']
                BLOCK_K: tl.constexpr = META['BLOCK_K']

                pid_m = tl.program_id(axis=0)
                pid_n = tl.program_id(axis=1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                for k in range(0, K, BLOCK_K):
                    k_idx = offs_k + k

                    a_ptrs = A + offs_m[:, None] * stride_am + k_idx[None, :] * stride_ak
                    b_ptrs = B + k_idx[:, None] * stride_bk + offs_n[None, :] * stride_bn

                    k_mask = k_idx < K
                    a_mask = (offs_m[:, None] < M) & (k_mask[None, :])
                    b_mask = (offs_n[None, :] < N) & (k_mask[:, None])

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b, out_dtype=tl.float32)

                acc = gelu(acc)

                c_ptrs = C + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc.to(C.dtype.element_ty), mask=c_mask)


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Input tensors must be 2D")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Incompatible matrix dimensions")
                if not a.is_cuda or not b.is_cuda:
                    raise ValueError("Inputs must be CUDA tensors")
                if a.device != b.device:
                    raise ValueError("Inputs must be on the same device")
                if a.dtype != b.dtype:
                    raise ValueError("Input dtypes must match")
                if a.dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    raise TypeError("Supported dtypes are float16, bfloat16, and float32")

                M, K = a.shape
                Kb, N = b.shape
                if Kb != K:
                    raise ValueError("Inner dimensions must match")

                c = torch.empty((M, N), device=a.device, dtype=a.dtype)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']),
                    triton.cdiv(N, META['BLOCK_N']),
                )

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                )

                return c
            '''
        )
        return {"code": code}
