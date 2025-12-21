import os
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
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 8},
                        num_stages=4, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32,  'GROUP_M': 8},
                        num_stages=4, num_warps=4
                    ),
                    triton.Config(
                        {'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32,  'GROUP_M': 8},
                        num_stages=4, num_warps=4
                    ),
                    triton.Config(
                        {'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32,  'GROUP_M': 8},
                        num_stages=4, num_warps=4
                    ),
                    triton.Config(
                        {'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 64,  'GROUP_M': 8},
                        num_stages=4, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 64,  'GROUP_M': 8},
                        num_stages=4, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64,  'GROUP_M': 8},
                        num_stages=5, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64,  'GROUP_M': 8},
                        num_stages=5, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64,  'GROUP_M': 8},
                        num_stages=5, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 4},
                        num_stages=3, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 128, 'GROUP_M': 4},
                        num_stages=3, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 4},
                        num_stages=3, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 128, 'GROUP_M': 4},
                        num_stages=3, num_warps=8
                    ),
                    triton.Config(
                        {'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 128, 'GROUP_M': 4},
                        num_stages=3, num_warps=8
                    ),
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
                ACT: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr,
            ):
                pid = tl.program_id(0)

                # Number of blocks
                num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
                num_pid_n = (N + BLOCK_N - 1) // BLOCK_N

                # Grouped ordering to improve L2 hit-rate
                group_size_m = GROUP_M
                num_pid_in_group = group_size_m * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * group_size_m
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + (pid_in_group % group_size_m)
                pid_n = (pid_in_group // group_size_m) % num_pid_n

                # Some blocks may be out of range
                if pid_m >= num_pid_m:
                    return

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (offs_m[:, None] * stride_am) + (offs_k[None, :] * stride_ak)
                b_ptrs = b_ptr + (offs_k[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k = 0
                while k < K:
                    k_remaining = K - k
                    k_mask = offs_k[None, :] < k_remaining
                    a_mask = (offs_m[:, None] < M) & k_mask
                    b_mask = k_mask.T & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k += BLOCK_K

                if ACT:
                    acc = gelu(acc)

                # Write-back with masks
                c = acc
                c_ptrs = c_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
                mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, c, mask=mask)


            def _grid(meta, M, N):
                return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("a and b must be 2D tensors")
                M, K1 = a.shape
                K2, N = b.shape
                if K1 != K2:
                    raise ValueError(f"Incompatible shapes: {a.shape} @ {b.shape}")
                K = K1

                if not a.is_cuda or not b.is_cuda:
                    # Fallback to torch.matmul + GELU on CPU
                    out = a @ b
                    return torch.nn.functional.gelu(out)

                # Promote dtype if needed; output dtype follows Torch default promotion
                if a.dtype == b.dtype:
                    out_dtype = a.dtype
                else:
                    out_dtype = torch.promote_types(a.dtype, b.dtype)

                # Output tensor; kernel writes float32 due to accumulation when ACT fused; cast handled by storage dtype
                # We keep output in out_dtype by casting inside the store path via implicit cast in tl.store.
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                # Extract strides (row-major: (stride(0), stride(1)))
                stride_am, stride_ak = a.stride()
                stride_bk, stride_bn = b.stride()
                stride_cm, stride_cn = c.stride()

                # Launch the kernel
                _matmul_gelu_kernel[
                    _grid
                ](
                    a, b, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                    ACT=True,
                    num_warps=None,
                    num_stages=None,
                )
                return c
            '''
        )
        return {"code": code}
