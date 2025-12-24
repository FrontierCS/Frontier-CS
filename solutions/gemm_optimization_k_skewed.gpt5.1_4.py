import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent('''\
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def matmul_kernel(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
                b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + offs_k

                    a_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
                    b_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


            def _gelu_torch(x: torch.Tensor) -> torch.Tensor:
                return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("matmul expects 2D tensors")
                if a.shape[1] != b.shape[0]:
                    raise ValueError(f"Incompatible shapes: {a.shape} and {b.shape}")

                M, K = a.shape
                Kb, N = b.shape

                if Kb != K:
                    raise ValueError(f"Incompatible shapes: {a.shape} and {b.shape}")

                if M == 0 or N == 0 or K == 0:
                    return _gelu_torch(a @ b)

                if not (a.is_cuda and b.is_cuda):
                    c = a.float() @ b.float()
                    c = _gelu_torch(c)
                    return c.to(a.dtype)

                if a.dtype != torch.float16 or b.dtype != torch.float16:
                    c = a @ b
                    return _gelu_torch(c)

                c = torch.empty((M, N), device=a.device, dtype=a.dtype)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']),
                    triton.cdiv(N, META['BLOCK_N']),
                )

                matmul_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                )

                return c
        ''')
        return {"code": code}
