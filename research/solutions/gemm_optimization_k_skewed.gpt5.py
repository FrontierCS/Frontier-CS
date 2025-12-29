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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 4}, num_stages=5, num_warps=8),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def _matmul_gelu_kernel(
                a_ptr, b_ptr, c_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                OUT_TYPE_ID: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)
                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)

                group_size_m = GROUP_M
                group_size = group_size_m * num_pid_n
                group_id = pid // group_size
                first_pid_m = group_id * group_size_m
                pid_in_group = pid % group_size
                group_size_m_eff = tl.minimum(num_pid_m - first_pid_m, group_size_m)
                pid_m = first_pid_m + (pid_in_group % group_size_m_eff)
                pid_n = pid_in_group // group_size_m_eff

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_iter = 0
                while k_iter < K:
                    k_remaining = K - k_iter
                    k_mask = offs_k < k_remaining
                    a_mask = (offs_m[:, None] < M) & k_mask[None, :]
                    b_mask = k_mask[:, None] & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b)

                    k_iter += BLOCK_K
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

                if OUT_TYPE_ID == 0:
                    out = acc.to(tl.float16)
                elif OUT_TYPE_ID == 1:
                    out = acc.to(tl.bfloat16)
                else:
                    out = acc
                tl.store(c_ptrs, out, mask=c_mask)

            def _dtype_id(dtype: torch.dtype) -> int:
                if dtype == torch.float16:
                    return 0
                if dtype == torch.bfloat16:
                    return 1
                return 2

            def _get_strides(t: torch.Tensor):
                s0, s1 = t.stride()
                return s0, s1

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                """
                Matrix multiplication with GELU activation.
                Args:
                    a: (M, K)
                    b: (K, N)
                Returns:
                    (M, N) with GELU activation applied
                """
                assert a.ndim == 2 and b.ndim == 2, "Input tensors must be 2D"
                assert a.shape[1] == b.shape[0], "Incompatible shapes"
                assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
                M, K = a.shape
                K2, N = b.shape
                out_dtype = torch.result_type(a, b)
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                stride_am, stride_ak = _get_strides(a)
                stride_bk, stride_bn = _get_strides(b)
                stride_cm, stride_cn = _get_strides(c)

                out_type_id = _dtype_id(out_dtype)

                def grid(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                    out_type_id,
                )
                return c
        """)
        return {"code": code}