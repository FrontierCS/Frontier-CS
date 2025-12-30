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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=5),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4, num_stages=5),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _matmul_gelu_kernel(
                A_ptr, B_ptr, C_ptr,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                OUT_DTYPE: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                k = 0
                while k < K:
                    k_remaining = K - k

                    a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < k_remaining)
                    b_mask = (offs_n[None, :] < N) & (offs_k[:, None] < k_remaining)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a.to(tl.float32), b.to(tl.float32))

                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk
                    k += BLOCK_K

                acc = gelu(acc)

                c_ptrs = C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

                acc_converted = acc.to(OUT_DTYPE)
                tl.store(c_ptrs, acc_converted, mask=c_mask)


            def _torch_dtype_to_triton(dtype: torch.dtype):
                if dtype == torch.float16:
                    return tl.float16
                if dtype == torch.bfloat16:
                    return tl.bfloat16
                if dtype == torch.float32:
                    return tl.float32
                # Default to float32 for unsupported dtypes
                return tl.float32


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Inputs must be 2D tensors")
                if a.shape[1] != b.shape[0]:
                    raise ValueError(f"Incompatible shapes for matmul: {a.shape} and {b.shape}")

                M, K = a.shape
                Kb, N = b.shape

                # Fallback to PyTorch if tensors are on CPU or not floating-point
                if (not a.is_cuda) or (not b.is_cuda):
                    c = a @ b
                    return torch.nn.functional.gelu(c)

                if a.dtype not in (torch.float16, torch.bfloat16, torch.float32) or \
                   b.dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    c = a @ b
                    return torch.nn.functional.gelu(c)

                out_dtype = torch.result_type(a, b)
                if out_dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    out_dtype = torch.float32

                C = torch.empty((M, N), device=a.device, dtype=out_dtype)

                stride_am, stride_ak = a.stride()
                stride_bk, stride_bn = b.stride()
                stride_cm, stride_cn = C.stride()

                out_triton_dtype = _torch_dtype_to_triton(out_dtype)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']),
                    triton.cdiv(N, META['BLOCK_N']),
                )

                _matmul_gelu_kernel[grid](
                    a, b, C,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                    OUT_DTYPE=out_triton_dtype,
                )

                return C
        ''')
        return {"code": code}