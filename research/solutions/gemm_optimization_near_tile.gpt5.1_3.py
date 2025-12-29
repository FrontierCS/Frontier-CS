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
                triton.Config(
                    {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
                    num_stages=2,
                    num_warps=4,
                ),
                triton.Config(
                    {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
                    num_stages=2,
                    num_warps=4,
                ),
                triton.Config(
                    {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
                    num_stages=2,
                    num_warps=4,
                ),
                triton.Config(
                    {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4},
                    num_stages=3,
                    num_warps=8,
                ),
                triton.Config(
                    {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4},
                    num_stages=3,
                    num_warps=8,
                ),
                triton.Config(
                    {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
                    num_stages=3,
                    num_warps=8,
                ),
                triton.Config(
                    {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4},
                    num_stages=3,
                    num_warps=8,
                ),
                triton.Config(
                    {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 2},
                    num_stages=3,
                    num_warps=8,
                ),
            ],
            key=[
                'M',
                'N',
                'K',
                'stride_am',
                'stride_ak',
                'stride_bk',
                'stride_bn',
                'stride_cm',
                'stride_cn',
                'DTYPE',
            ],
        )
        @triton.jit
        def _matmul_kernel(
            A, B, C,
            M, N, K,
            stride_am, stride_ak,
            stride_bk, stride_bn,
            stride_cm, stride_cn,
            DTYPE: tl.constexpr,
            BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            GROUP_M: tl.constexpr,
        ):
            pid = tl.program_id(axis=0)

            num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
            num_pid_n = (N + BLOCK_N - 1) // BLOCK_N

            group_size = GROUP_M
            num_pid_in_group = group_size * num_pid_n
            group_id = pid // num_pid_in_group
            first_pid_m = group_id * group_size
            pid_in_group = pid % num_pid_in_group
            pid_m = first_pid_m + (pid_in_group % group_size)
            pid_n = pid_in_group // group_size

            offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

            mask_m = offs_m < M
            mask_n = offs_n < N

            offs_k = tl.arange(0, BLOCK_K)

            acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

            for k in range(0, K, BLOCK_K):
                k_current = k + offs_k
                k_mask = k_current < K

                a_ptrs = A + (offs_m[:, None] * stride_am + k_current[None, :] * stride_ak)
                b_ptrs = B + (k_current[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                a_mask = mask_m[:, None] & k_mask[None, :]
                b_mask = k_mask[:, None] & mask_n[None, :]

                a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                acc += tl.dot(a, b)

            acc = gelu(acc)

            if DTYPE == 0:
                c = acc.to(tl.float16)
            elif DTYPE == 1:
                c = acc
            elif DTYPE == 2:
                c = acc.to(tl.bfloat16)
            else:
                c = acc

            c_ptrs = C + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
            c_mask = mask_m[:, None] & mask_n[None, :]

            tl.store(c_ptrs, c, mask=c_mask)


        def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
            assert a.dim() == 2 and b.dim() == 2, "matmul expects 2D tensors"
            assert a.shape[1] == b.shape[0], "incompatible matrix dimensions"

            if not a.is_cuda or not b.is_cuda:
                return torch.nn.functional.gelu(a @ b)

            assert a.device == b.device, "input tensors must be on the same device"

            dtype = a.dtype
            assert dtype == b.dtype, "input tensors must have the same dtype"

            if dtype == torch.float16:
                DTYPE = 0
            elif dtype == torch.float32:
                DTYPE = 1
            elif dtype == torch.bfloat16:
                DTYPE = 2
            else:
                # Fallback for unsupported dtypes
                return torch.nn.functional.gelu(a @ b)

            M, K = a.shape
            K2, N = b.shape
            assert K2 == K

            c = torch.empty((M, N), device=a.device, dtype=dtype)

            stride_am, stride_ak = a.stride()
            stride_bk, stride_bn = b.stride()
            stride_cm, stride_cn = c.stride()

            grid = lambda META: (
                triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
            )

            _matmul_kernel[grid](
                a, b, c,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                DTYPE,
            )

            return c
        """)
        return {"code": code}