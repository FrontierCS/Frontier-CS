import torch
import triton
import triton.language as tl
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


            @triton.autotune(
                configs=[
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_stages=3, num_warps=8),
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_stages=3, num_warps=4),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32}, num_stages=3, num_warps=4),
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_stages=3, num_warps=4),
                    triton.Config({"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 32}, num_stages=2, num_warps=4),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 32, "BLOCK_K": 32}, num_stages=2, num_warps=4),
                ],
                key=["M", "N", "K"],
            )
            @triton.jit
            def matmul_kernel(
                a_ptr, b_ptr, c_ptr,
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

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + offs_k

                    a_ptrs = a_ptr + offs_m[:, None] * stride_am + k_offsets[None, :] * stride_ak
                    b_ptrs = b_ptr + k_offsets[:, None] * stride_bk + offs_n[None, :] * stride_bn

                    a_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
                    b_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    acc += tl.dot(a, b, out_dtype=tl.float32)

                acc = gelu(acc)

                c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
                c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

                if OUT_DTYPE == 0:
                    out = acc
                elif OUT_DTYPE == 1:
                    out = acc.to(tl.float16)
                elif OUT_DTYPE == 2:
                    out = acc.to(tl.bfloat16)
                else:
                    out = acc

                tl.store(c_ptrs, out, mask=c_mask)


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.ndim != 2 or b.ndim != 2:
                    raise ValueError("Inputs must be 2D matrices")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Incompatible matrix shapes for multiplication")

                if not (a.is_cuda and b.is_cuda):
                    c = torch.matmul(a, b)
                    return torch.nn.functional.gelu(c)

                M, K = a.shape
                Kb, N = b.shape
                if Kb != K:
                    raise ValueError("Inner dimensions must match")

                device = a.device
                if b.device != device:
                    b = b.to(device)

                out_dtype = torch.result_type(a, b)
                if out_dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    out_dtype = torch.float32

                c = torch.empty((M, N), device=device, dtype=out_dtype)

                stride_am, stride_ak = a.stride()
                stride_bk, stride_bn = b.stride()
                stride_cm, stride_cn = c.stride()

                if out_dtype == torch.float32:
                    out_type_id = 0
                elif out_dtype == torch.float16:
                    out_type_id = 1
                else:  # torch.bfloat16
                    out_type_id = 2

                def grid(meta):
                    return (
                        triton.cdiv(M, meta["BLOCK_M"]),
                        triton.cdiv(N, meta["BLOCK_N"]),
                    )

                matmul_kernel[grid](
                    a, b, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                    OUT_DTYPE=out_type_id,
                )

                return c
            '''
        )
        return {"code": kernel_code}
