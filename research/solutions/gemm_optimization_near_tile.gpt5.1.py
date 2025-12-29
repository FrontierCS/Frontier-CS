import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import torch.nn.functional as F
            import triton
            import triton.language as tl


            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


            @triton.autotune(
                configs=[
                    triton.Config(
                        {
                            "BLOCK_M": 64,
                            "BLOCK_N": 64,
                            "BLOCK_K": 32,
                        },
                        num_warps=4,
                        num_stages=2,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 64,
                            "BLOCK_N": 128,
                            "BLOCK_K": 32,
                        },
                        num_warps=4,
                        num_stages=2,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 128,
                            "BLOCK_N": 64,
                            "BLOCK_K": 32,
                        },
                        num_warps=4,
                        num_stages=2,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 128,
                            "BLOCK_N": 128,
                            "BLOCK_K": 32,
                        },
                        num_warps=8,
                        num_stages=3,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 64,
                            "BLOCK_N": 64,
                            "BLOCK_K": 128,
                        },
                        num_warps=4,
                        num_stages=3,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 64,
                            "BLOCK_N": 256,
                            "BLOCK_K": 64,
                        },
                        num_warps=8,
                        num_stages=3,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 256,
                            "BLOCK_N": 64,
                            "BLOCK_K": 64,
                        },
                        num_warps=8,
                        num_stages=3,
                    ),
                    triton.Config(
                        {
                            "BLOCK_M": 128,
                            "BLOCK_N": 128,
                            "BLOCK_K": 64,
                        },
                        num_warps=8,
                        num_stages=4,
                    ),
                ],
                key=[
                    "M",
                    "N",
                    "K",
                    "a_stride_am",
                    "a_stride_ak",
                    "b_stride_bk",
                    "b_stride_bn",
                ],
            )
            @triton.jit
            def matmul_kernel(
                a_ptr,
                b_ptr,
                c_ptr,
                M,
                N,
                K,
                a_stride_am,
                a_stride_ak,
                b_stride_bk,
                b_stride_bn,
                c_stride_cm,
                c_stride_cn,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(axis=0)
                pid_n = tl.program_id(axis=1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                a_ptrs = a_ptr + (
                    offs_m[:, None] * a_stride_am + offs_k[None, :] * a_stride_ak
                )
                b_ptrs = b_ptr + (
                    offs_k[:, None] * b_stride_bk + offs_n[None, :] * b_stride_bn
                )

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_remaining = K
                while k_remaining > 0:
                    k_mask = offs_k < k_remaining

                    a_mask = (offs_m[:, None] < M) & k_mask[None, :]
                    b_mask = k_mask[:, None] & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b)

                    a_ptrs += BLOCK_K * a_stride_ak
                    b_ptrs += BLOCK_K * b_stride_bk
                    k_remaining -= BLOCK_K

                acc = gelu(acc)

                c_ptrs = c_ptr + (
                    offs_m[:, None] * c_stride_cm + offs_n[None, :] * c_stride_cn
                )
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(c_ptrs, acc, mask=c_mask)


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("matmul expects 2D tensors")

                if a.shape[1] != b.shape[0]:
                    raise ValueError(
                        f"Incompatible shapes for matmul: {tuple(a.shape)} and {tuple(b.shape)}"
                    )

                if a.device.type != "cuda" or b.device.type != "cuda":
                    c = a @ b
                    return F.gelu(c)

                if a.dtype != b.dtype:
                    raise ValueError("Input tensors must have the same dtype")

                if a.dtype not in (
                    torch.float16,
                    torch.bfloat16,
                    torch.float32,
                ):
                    c = a @ b
                    return F.gelu(c)

                M, K = a.shape
                Kb, N = b.shape
                assert K == Kb

                a_stride_am, a_stride_ak = a.stride()
                b_stride_bk, b_stride_bn = b.stride()

                c = torch.empty((M, N), device=a.device, dtype=a.dtype)
                c_stride_cm, c_stride_cn = c.stride()

                grid = lambda META: (
                    triton.cdiv(M, META["BLOCK_M"]),
                    triton.cdiv(N, META["BLOCK_N"]),
                )

                matmul_kernel[grid](
                    a,
                    b,
                    c,
                    M,
                    N,
                    K,
                    a_stride_am,
                    a_stride_ak,
                    b_stride_bk,
                    b_stride_bn,
                    c_stride_cm,
                    c_stride_cn,
                )

                return c
            """
        )
        return {"code": code}