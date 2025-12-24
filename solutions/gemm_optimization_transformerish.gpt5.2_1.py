import math
import os
from typing import Dict, Optional

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_MATMUL_CONFIGS = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 64, "GROUP_M": 4}, num_warps=8, num_stages=5),
]


@triton.autotune(configs=_MATMUL_CONFIGS, key=["M", "N", "K"])
@triton.heuristics(
    {
        "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
        "EVEN_M": lambda args: (args["M"] % args["BLOCK_M"]) == 0,
        "EVEN_N": lambda args: (args["N"] % args["BLOCK_N"]) == 0,
    }
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ak: tl.constexpr,
    stride_bk: tl.constexpr,
    stride_bn: tl.constexpr,
    stride_cm: tl.constexpr,
    stride_cn: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    tl.multiple_of(offs_k, 16)
    tl.multiple_of(offs_m, 8)
    tl.multiple_of(offs_n, 8)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_M and EVEN_N and EVEN_K:
        for _ in range(0, K, BLOCK_K):
            a = tl.load(a_ptrs)
            b = tl.load(b_ptrs)
            acc = tl.dot(a, b, acc, out_dtype=tl.float32)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    else:
        m_mask = offs_m < M
        n_mask = offs_n < N
        for k in range(0, K, BLOCK_K):
            if EVEN_K:
                if EVEN_M:
                    a = tl.load(a_ptrs)
                else:
                    a = tl.load(a_ptrs, mask=m_mask[:, None], other=0.0)
                if EVEN_N:
                    b = tl.load(b_ptrs)
                else:
                    b = tl.load(b_ptrs, mask=n_mask[None, :], other=0.0)
            else:
                k_mask = (k + offs_k) < K
                if EVEN_M:
                    a = tl.load(a_ptrs, mask=k_mask[None, :], other=0.0)
                else:
                    a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
                if EVEN_N:
                    b = tl.load(b_ptrs, mask=k_mask[:, None], other=0.0)
                else:
                    b = tl.load(b_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            acc = tl.dot(a, b, acc, out_dtype=tl.float32)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk

    out = gelu(acc)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    if EVEN_M and EVEN_N:
        tl.store(c_ptrs, out)
    else:
        tl.store(c_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def _gelu_torch(x: torch.Tensor) -> torch.Tensor:
    return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not isinstance(a, torch.Tensor) or not isinstance(b, torch.Tensor):
        raise TypeError("matmul expects torch.Tensor inputs")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")
    if a.device != b.device:
        raise ValueError("a and b must be on the same device")
    if a.numel() == 0 or b.numel() == 0:
        return _gelu_torch(a @ b)

    if a.device.type != "cuda":
        return _gelu_torch(a @ b)

    if a.dtype != b.dtype:
        common = torch.promote_types(a.dtype, b.dtype)
        a = a.to(common)
        b = b.to(common)

    if a.dtype not in (torch.float16, torch.bfloat16):
        return _gelu_torch(a @ b)

    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError("incompatible shapes")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        K=K,
        stride_am=stride_am,
        stride_ak=stride_ak,
        stride_bk=stride_bk,
        stride_bn=stride_bn,
        stride_cm=stride_cm,
        stride_cn=stride_cn,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"program_path": os.path.abspath(__file__)}
