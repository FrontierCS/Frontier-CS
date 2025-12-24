import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                ],
                key=['M', 'N', 'K', 'a_stride_am', 'a_stride_ak', 'b_stride_bk', 'b_stride_bn'],
            )
            @triton.jit
            def matmul_kernel(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                a_stride_am, a_stride_ak,
                b_stride_bk, b_stride_bn,
                c_stride_cm, c_stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * a_stride_am + offs_k[None, :] * a_stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * b_stride_bk + offs_n[None, :] * b_stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k = 0
                while k < K:
                    k_remaining = K - k
                    k_mask = offs_k < k_remaining

                    a_mask = (offs_m[:, None] < M) & k_mask[None, :]
                    b_mask = k_mask[:, None] & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    a = a.to(tl.float32)
                    b = b.to(tl.float32)

                    acc += tl.dot(a, b)

                    k += BLOCK_K
                    a_ptrs += BLOCK_K * a_stride_ak
                    b_ptrs += BLOCK_K * b_stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * c_stride_cm + offs_n[None, :] * c_stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc, mask=c_mask)


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                assert a.ndim == 2 and b.ndim == 2, "Input tensors must be 2D"
                assert a.shape[1] == b.shape[0], "Incompatible matrix shapes"
                assert a.is_cuda and b.is_cuda, "Input tensors must be on CUDA device"
                assert a.dtype == b.dtype, "Input tensors must have the same dtype"

                M, K = a.shape
                K2, N = b.shape
                assert K == K2

                if M == 0 or N == 0 or K == 0:
                    return torch.zeros((M, N), device=a.device, dtype=a.dtype)

                c = torch.empty((M, N), device=a.device, dtype=a.dtype)

                a_stride_am, a_stride_ak = a.stride()
                b_stride_bk, b_stride_bn = b.stride()
                c_stride_cm, c_stride_cn = c.stride()

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']),
                    triton.cdiv(N, META['BLOCK_N']),
                )

                matmul_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a_stride_am, a_stride_ak,
                    b_stride_bk, b_stride_bn,
                    c_stride_cm, c_stride_cn,
                )
                return c
            """
        )
        return {"code": code}
