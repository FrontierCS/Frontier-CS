import os
import sys
import inspect
import torch

try:
    import triton
    import triton.language as tl
except Exception:  # pragma: no cover
    triton = None
    tl = None


if triton is not None:

    @triton.jit
    def gelu(x):
        return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

    _MATMUL_CONFIGS = [
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    ]

    @triton.autotune(configs=_MATMUL_CONFIGS, key=["M", "N", "K"])
    @triton.jit
    def _matmul_gelu_kernel(
        A_ptr,
        B_ptr,
        C_ptr,
        M: tl.constexpr,
        N: tl.constexpr,
        K: tl.constexpr,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        ALLOW_TF32: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(axis=0)

        num_pid_m = tl.cdiv(M, BLOCK_M)
        num_pid_n = tl.cdiv(N, BLOCK_N)
        pid_group = pid // (num_pid_n * GROUP_M)
        first_pid_m = pid_group * GROUP_M
        pid_in_group = pid % (num_pid_n * GROUP_M)
        pid_m = first_pid_m + (pid_in_group % GROUP_M)
        pid_n = pid_in_group // GROUP_M

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k_iter = 0
        k_remaining = K
        while k_remaining > 0:
            k_mask = (k_iter * BLOCK_K + offs_k) < K
            a = tl.load(
                a_ptrs,
                mask=(offs_m[:, None] < M) & (k_mask[None, :]),
                other=0.0,
            )
            b = tl.load(
                b_ptrs,
                mask=(k_mask[:, None]) & (offs_n[None, :] < N),
                other=0.0,
            )
            acc += tl.dot(a, b, allow_tf32=ALLOW_TF32)

            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k_iter += 1
            k_remaining -= BLOCK_K

        acc = gelu(acc)

        c_ptrs = C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
        tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if triton is None or (not a.is_cuda) or (not b.is_cuda):
        c = a @ b
        return torch.nn.functional.gelu(c, approximate="none")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors a:(M,K), b:(K,N)")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"shape mismatch: a:{tuple(a.shape)} b:{tuple(b.shape)}")

    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError(f"shape mismatch: a:{tuple(a.shape)} b:{tuple(b.shape)}")

    out_dtype = a.dtype
    if out_dtype not in (torch.float16, torch.bfloat16, torch.float32):
        a = a.to(torch.float16)
        b = b.to(torch.float16)
        out_dtype = torch.float16

    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    allow_tf32 = bool(a.dtype == torch.float32 and b.dtype == torch.float32)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        K=K,
        stride_am=a.stride(0),
        stride_ak=a.stride(1),
        stride_bk=b.stride(0),
        stride_bn=b.stride(1),
        stride_cm=c.stride(0),
        stride_cn=c.stride(1),
        ALLOW_TF32=allow_tf32,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except Exception:
            pass
        try:
            code = inspect.getsource(sys.modules[__name__])
            return {"code": code}
        except Exception:
            return {"code": ""}