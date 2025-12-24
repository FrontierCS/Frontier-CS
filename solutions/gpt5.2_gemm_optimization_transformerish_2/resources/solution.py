import os
import math
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.jit
    def gelu(x):
        return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

    _MATMUL_CONFIGS = [
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=3),
    ]

    @triton.autotune(configs=_MATMUL_CONFIGS, key=["M", "N", "K"])
    @triton.heuristics(
        {
            "EVEN_M": lambda args: (args["M"] % args["BLOCK_M"]) == 0,
            "EVEN_N": lambda args: (args["N"] % args["BLOCK_N"]) == 0,
            "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
        }
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
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
        EVEN_M: tl.constexpr,
        EVEN_N: tl.constexpr,
        EVEN_K: tl.constexpr,
    ):
        pid = tl.program_id(0)

        num_pid_m = tl.cdiv(M, BLOCK_M)
        num_pid_n = tl.cdiv(N, BLOCK_N)

        group_m = GROUP_M
        pid_group = pid // (group_m * num_pid_n)
        first_pid_m = pid_group * group_m
        pid_in_group = pid - pid_group * (group_m * num_pid_n)
        pid_m = first_pid_m + (pid_in_group % group_m)
        pid_n = pid_in_group // group_m

        if pid_m >= num_pid_m:
            return

        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        rk = tl.arange(0, BLOCK_K)

        if EVEN_M:
            m_mask = tl.full((BLOCK_M,), True, tl.int1)
        else:
            m_mask = rm < M
        if EVEN_N:
            n_mask = tl.full((BLOCK_N,), True, tl.int1)
        else:
            n_mask = rn < N

        a_ptrs = a_ptr + (rm[:, None] * stride_am + rk[None, :] * stride_ak)
        b_ptrs = b_ptr + (rk[:, None] * stride_bk + rn[None, :] * stride_bn)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            if EVEN_K:
                a = tl.load(a_ptrs, mask=m_mask[:, None], other=0.0)
                b = tl.load(b_ptrs, mask=n_mask[None, :], other=0.0)
            else:
                k_mask = rk < (K - k)
                a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
                b = tl.load(b_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            acc = tl.dot(a, b, acc)

            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k += BLOCK_K

        acc = gelu(acc)

        c_ptrs = c_ptr + (rm[:, None] * stride_cm + rn[None, :] * stride_cn)

        if EVEN_M and EVEN_N:
            tl.store(c_ptrs, acc)
        else:
            tl.store(c_ptrs, acc, mask=m_mask[:, None] & n_mask[None, :])


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if triton is None or tl is None or (not torch.cuda.is_available()):
        return torch.nn.functional.gelu(a @ b)

    if not (a.is_cuda and b.is_cuda):
        return torch.nn.functional.gelu(a @ b)

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")

    M, K = a.shape
    K2, N = b.shape
    if K != K2:
        raise ValueError(f"Incompatible shapes: a is {a.shape}, b is {b.shape}")

    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        raise TypeError(f"Unsupported dtype for a: {a.dtype}")
    if b.dtype != a.dtype:
        b = b.to(dtype=a.dtype)

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        K,
        a.stride(0),
        a.stride(1),
        b.stride(0),
        b.stride(1),
        c.stride(0),
        c.stride(1),
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": os.path.abspath(__file__)}
        except Exception:
            import inspect
            import sys

            return {"code": inspect.getsource(sys.modules[__name__])}
