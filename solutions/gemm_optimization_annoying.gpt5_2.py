import math
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import math
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0) * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

            def _init_to_zero(M):
                return tl.zeros((M, ), dtype=tl.int1)

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 8},  num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32,  'GROUP_M': 8},  num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 8},  num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64,  'GROUP_M': 8},  num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32,  'GROUP_M': 4},  num_stages=3, num_warps=16),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 4},  num_stages=3, num_warps=16),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32,  'GROUP_M': 8},  num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32,  'GROUP_M': 8},  num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 64,  'GROUP_M': 8},  num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32,  'BLOCK_K': 64,  'GROUP_M': 8},  num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 32,  'BLOCK_K': 64,  'GROUP_M': 8},  num_stages=4, num_warps=2),
                    triton.Config({'BLOCK_M': 32,  'BLOCK_N': 64,  'BLOCK_K': 64,  'GROUP_M': 8},  num_stages=4, num_warps=2),
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
                # meta-parameters
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)

                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)
                group_size_m = GROUP_M
                num_pid_in_group = group_size_m * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * group_size_m
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + (pid_in_group % group_size_m)
                pid_n = pid_in_group // group_size_m

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
                    a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask[None, :], other=0.0)
                    b = tl.load(b_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
                    acc += tl.dot(a, b)
                    k_iter += BLOCK_K
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

            def _get_blocking(M, N, K):
                # Lightweight heuristic to bias grid launch for very small sizes
                # Not used directly for tile selection (autotune handles that),
                # but could be extended for custom logic if needed.
                return

            def _promote_dtype(a_dtype, b_dtype):
                # Promote to a common dtype supported by Triton dot
                float_dtypes = {torch.float16, torch.bfloat16, torch.float32}
                if a_dtype not in float_dtypes or b_dtype not in float_dtypes:
                    return torch.float32
                if a_dtype == b_dtype:
                    return a_dtype
                # Prefer higher precision among the two
                if torch.float32 in (a_dtype, b_dtype):
                    return torch.float32
                if torch.bfloat16 in (a_dtype, b_dtype):
                    # If one is bf16 and other is fp16, choose bf16
                    return torch.bfloat16
                return torch.float16

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                """
                Matrix multiplication with GELU activation.
                a: (M, K), b: (K, N)
                Returns: (M, N)
                """
                if not (a.is_cuda and b.is_cuda):
                    raise RuntimeError("Tensors must be on CUDA device for Triton kernel.")
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Input tensors must be 2D.")
                M, K1 = a.shape
                K2, N = b.shape
                if K1 != K2:
                    raise ValueError("Inner dimensions must match: a.shape[1] == b.shape[0].")
                K = K1

                # Ensure dtypes are compatible; promote if needed
                out_dtype = _promote_dtype(a.dtype, b.dtype)
                if a.dtype != out_dtype:
                    a_ = a.to(out_dtype)
                else:
                    a_ = a
                if b.dtype != out_dtype:
                    b_ = b.to(out_dtype)
                else:
                    b_ = b

                # Allocate output; we store in same dtype as promoted input
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                # Strides in element units
                stride_am = a_.stride(0)
                stride_ak = a_.stride(1)
                stride_bk = b_.stride(0)
                stride_bn = b_.stride(1)
                stride_cm = c.stride(0)
                stride_cn = c.stride(1)

                def grid(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

                _matmul_gelu_kernel[grid](
                    a_, b_, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                )
                return c
        """)
        return {"code": code}
