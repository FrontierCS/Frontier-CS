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
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
                        num_stages=3,
                        num_warps=8,
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
                        num_stages=3,
                        num_warps=4,
                    ),
                    triton.Config(
                        {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
                        num_stages=3,
                        num_warps=4,
                    ),
                    triton.Config(
                        {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
                        num_stages=3,
                        num_warps=4,
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
                        num_stages=4,
                        num_warps=8,
                    ),
                    triton.Config(
                        {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4},
                        num_stages=4,
                        num_warps=8,
                    ),
                    triton.Config(
                        {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
                        num_stages=4,
                        num_warps=8,
                    ),
                    triton.Config(
                        {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4},
                        num_stages=4,
                        num_warps=8,
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4},
                        num_stages=4,
                        num_warps=8,
                    ),
                    triton.Config(
                        {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8},
                        num_stages=4,
                        num_warps=4,
                    ),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _matmul_gelu_kernel(
                a_ptr,
                b_ptr,
                c_ptr,
                M,
                N,
                K,
                stride_am,
                stride_ak,
                stride_bk,
                stride_bn,
                stride_cm,
                stride_cn,
                C_DTYPE: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)

                grid_m = tl.cdiv(M, BLOCK_M)
                grid_n = tl.cdiv(N, BLOCK_N)

                group_size = GROUP_M * grid_n
                group_id = pid // group_size
                first_pid_m = group_id * GROUP_M
                pid_in_group = pid % group_size
                pid_m = first_pid_m + (pid_in_group % GROUP_M)
                pid_n = pid_in_group // GROUP_M

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + offs_k
                    k_mask = k_offsets < K

                    a_ptrs = (
                        a_ptr
                        + offs_m[:, None] * stride_am
                        + k_offsets[None, :] * stride_ak
                    )
                    b_ptrs = (
                        b_ptr
                        + k_offsets[:, None] * stride_bk
                        + offs_n[None, :] * stride_bn
                    )

                    a = tl.load(
                        a_ptrs,
                        mask=(offs_m[:, None] < M) & k_mask[None, :],
                        other=0.0,
                    )
                    b = tl.load(
                        b_ptrs,
                        mask=k_mask[:, None] & (offs_n[None, :] < N),
                        other=0.0,
                    )

                    acc += tl.dot(a, b)

                c = gelu(acc)
                c = c.to(C_DTYPE)

                mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                c_ptrs = (
                    c_ptr
                    + offs_m[:, None] * stride_cm
                    + offs_n[None, :] * stride_cn
                )
                tl.store(c_ptrs, c, mask=mask)


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if not isinstance(a, torch.Tensor) or not isinstance(b, torch.Tensor):
                    raise TypeError("Inputs must be torch.Tensors")

                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Inputs must be 2D tensors of shape (M, K) and (K, N)")

                M, K_a = a.shape
                K_b, N = b.shape
                if K_a != K_b:
                    raise ValueError("Inner dimensions must match")

                if a.device.type != "cuda" or b.device.type != "cuda":
                    # Fallback to PyTorch on CPU or non-CUDA devices
                    return torch.nn.functional.gelu(a @ b)

                if a.dtype != b.dtype:
                    raise ValueError("Input dtypes must match")

                dtype = a.dtype
                if dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    # Fallback for unsupported dtypes
                    return torch.nn.functional.gelu(a @ b)

                out = torch.empty((M, N), device=a.device, dtype=dtype)

                stride_am, stride_ak = a.stride()
                stride_bk, stride_bn = b.stride()
                stride_cm, stride_cn = out.stride()

                if dtype == torch.float16:
                    C_DTYPE = tl.float16
                elif dtype == torch.bfloat16:
                    C_DTYPE = tl.bfloat16
                else:
                    C_DTYPE = tl.float32

                def grid(meta):
                    return (
                        triton.cdiv(M, meta['BLOCK_M'])
                        * triton.cdiv(N, meta['BLOCK_N']),
                    )

                _matmul_gelu_kernel[grid](
                    a,
                    b,
                    out,
                    M,
                    N,
                    K_a,
                    stride_am,
                    stride_ak,
                    stride_bk,
                    stride_bn,
                    stride_cm,
                    stride_cn,
                    C_DTYPE=C_DTYPE,
                )

                return out
            """
        )
        return {"code": code}
