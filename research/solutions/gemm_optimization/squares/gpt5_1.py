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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
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
                DTYPE: tl.constexpr,  # 0: fp16, 1: bf16, 2: fp32
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)

                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)
                grid = num_pid_m * num_pid_n

                group_size = GROUP_M
                group_num = (num_pid_m + group_size - 1) // group_size
                group_id = pid // (group_size * num_pid_n)
                group_id = tl.minimum(group_id, group_num - 1)
                first_pid_m = group_id * group_size
                pid_in_group = pid - group_id * group_size * num_pid_n
                pid_m = first_pid_m + (pid_in_group % group_size)
                pid_n = pid_in_group // group_size

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_loops = tl.cdiv(K, BLOCK_K)
                for k in range(0, k_loops):
                    k_off = k * BLOCK_K
                    a_mask = (offs_m[:, None] < M) & (k_off + offs_k[None, :] < K)
                    b_mask = (k_off + offs_k[:, None] < K) & (offs_n[None, :] < N)
                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                    if DTYPE == 0:
                        a = a.to(tl.float16)
                        b = b.to(tl.float16)
                    elif DTYPE == 1:
                        a = a.to(tl.bfloat16)
                        b = b.to(tl.bfloat16)
                    else:
                        a = a.to(tl.float32)
                        b = b.to(tl.float32)
                    acc += tl.dot(a, b)
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                # Write back
                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                if DTYPE == 0:
                    out = acc.to(tl.float16)
                elif DTYPE == 1:
                    out = acc.to(tl.bfloat16)
                else:
                    out = acc.to(tl.float32)
                tl.store(c_ptrs, out, mask=c_mask)

            def _get_dtype_code(dtype: torch.dtype) -> int:
                if dtype == torch.float16:
                    return 0
                if dtype == torch.bfloat16:
                    return 1
                if dtype == torch.float32:
                    return 2
                # Fallback: run in fp32
                return 2

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                """
                Matrix multiplication with GELU activation.
                Args:
                    a: Input tensor of shape (M, K)
                    b: Input tensor of shape (K, N)
                Returns:
                    Output tensor of shape (M, N) with GELU activation applied
                """
                assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
                assert a.shape[1] == b.shape[0], "Incompatible shapes"
                M, K = a.shape
                Kb, N = b.shape
                dtype = a.dtype
                # If dtypes mismatch, cast b to a's dtype for consistency
                if b.dtype != dtype:
                    b = b.to(dtype)

                # Ensure contiguous strides are handled; we pass strides explicitly
                a_contig = a
                b_contig = b
                # Allocate output
                c = torch.empty((M, N), device=a.device, dtype=dtype)

                # Compute strides in elements
                stride_am, stride_ak = a_contig.stride()
                stride_bk, stride_bn = b_contig.stride()
                stride_cm, stride_cn = c.stride()

                grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

                dtype_code = _get_dtype_code(dtype)

                _matmul_gelu_kernel[grid](
                    a_contig, b_contig, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                    DTYPE=dtype_code,
                )
                return c
        """)
        return {"code": code}