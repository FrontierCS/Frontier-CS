import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent('''
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),

                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=5, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=5, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=5, num_warps=8),

                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),

                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
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
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr
            ):
                pid = tl.program_id(axis=0)

                # Blocks along M and N
                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)

                group_size = GROUP_M
                num_pid_in_group = group_size * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * group_size
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + (pid_in_group % group_size)
                pid_n = pid_in_group // group_size

                # guard for out-of-range program ids
                if pid_m >= num_pid_m:
                    return

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_remaining = K
                # main loop
                while k_remaining > 0:
                    k_mask = offs_k[None, :] < k_remaining
                    a_mask = (offs_m[:, None] < M) & k_mask
                    b_mask = k_mask.T & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k_remaining -= BLOCK_K

                # Apply GELU activation in-kernel
                acc = gelu(acc)

                c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc, mask=c_mask)

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                """
                Matrix multiplication with GELU activation.

                Args:
                    a: Input tensor of shape (M, K)
                    b: Input tensor of shape (K, N)

                Returns:
                    Output tensor of shape (M, N) with GELU activation applied
                """
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Inputs must be 2D tensors")
                M, K = a.shape
                Kb, N = b.shape
                if K != Kb:
                    raise ValueError(f"Incompatible shapes: {a.shape} @ {b.shape}")

                if not a.is_cuda or not b.is_cuda:
                    raise RuntimeError("Inputs must be CUDA tensors")

                # Choose output dtype
                # Accumulate in fp32; store in promoted dtype
                out_dtype = torch.promote_types(a.dtype, b.dtype)
                if out_dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    # Fallback to fp32 if unsupported dtype
                    out_dtype = torch.float32

                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                # Strides
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
                    stride_cm, stride_cn
                )
                return c
        ''')
        return {"code": code}
