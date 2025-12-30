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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=3),
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
                GROUP_M: tl.constexpr,
            ):
                pid = tl.program_id(0)
                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)
                num_pid_in_group = GROUP_M * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * GROUP_M
                group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + (pid_in_group % group_size_m)
                pid_n = (pid_in_group // group_size_m)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                offs_m_i64 = offs_m.to(tl.int64)
                offs_n_i64 = offs_n.to(tl.int64)
                offs_k_i64 = offs_k.to(tl.int64)

                a_ptrs = a_ptr + offs_m_i64[:, None] * stride_am + offs_k_i64[None, :] * stride_ak
                b_ptrs = b_ptr + offs_k_i64[:, None] * stride_bk + offs_n_i64[None, :] * stride_bn

                mask_m = offs_m[:, None] < M
                mask_n = offs_n[None, :] < N

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k = 0
                EVEN_K = (K % BLOCK_K) == 0
                while k < K:
                    if EVEN_K:
                        a = tl.load(a_ptrs, mask=mask_m, other=0.0)
                        b = tl.load(b_ptrs, mask=mask_n, other=0.0)
                    else:
                        k_remaining = K - k
                        kmask_a = offs_k[None, :] < k_remaining
                        kmask_b = offs_k[:, None] < k_remaining
                        a = tl.load(a_ptrs, mask=mask_m & kmask_a, other=0.0)
                        b = tl.load(b_ptrs, mask=mask_n & kmask_b, other=0.0)

                    acc += tl.dot(a, b)

                    k += BLOCK_K
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + offs_m_i64[:, None] * stride_cm + offs_n_i64[None, :] * stride_cn
                mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc, mask=mask_c)

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                \"""
                Matrix multiplication with GELU activation.

                Args:
                    a: Input tensor of shape (M, K)
                    b: Input tensor of shape (K, N)

                Returns:
                    Output tensor of shape (M, N) with GELU activation applied
                \"""
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Inputs must be 2D tensors")
                if a.shape[1] != b.shape[0]:
                    raise ValueError(f"Incompatible dimensions: a.shape={tuple(a.shape)}, b.shape={tuple(b.shape)}")
                if not a.is_cuda or not b.is_cuda:
                    raise ValueError("Inputs must be CUDA tensors")
                M, K = a.shape
                K2, N = b.shape
                assert K == K2

                # Output dtype follows PyTorch's result_type promotion
                out_dtype = torch.result_type(a, b)
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                # Extract element-wise strides
                stride_am = a.stride(0)
                stride_ak = a.stride(1)
                stride_bk = b.stride(0)
                stride_bn = b.stride(1)
                stride_cm = c.stride(0)
                stride_cn = c.stride(1)

                def grid(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                )
                return c
        """)
        return {"code": code}