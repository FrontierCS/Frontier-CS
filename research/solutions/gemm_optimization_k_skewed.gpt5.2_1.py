import math
import os
import textwrap
from typing import Dict, Optional

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _configs():
    cfgs = []
    for BM, BN, BK, warps, stages, group_m in [
        (128, 128, 32, 8, 4, 8),
        (128, 64, 32, 4, 4, 8),
        (64, 128, 32, 4, 4, 8),
        (64, 64, 32, 4, 4, 8),
        (128, 128, 64, 8, 5, 8),
        (128, 64, 64, 4, 5, 8),
        (64, 128, 64, 4, 5, 8),
        (64, 64, 64, 4, 5, 8),
        (256, 64, 32, 8, 4, 4),
        (64, 256, 32, 8, 4, 4),
        (256, 128, 32, 8, 4, 4),
        (128, 256, 32, 8, 4, 4),
        (128, 128, 128, 8, 6, 4),
        (128, 64, 128, 4, 6, 4),
        (64, 128, 128, 4, 6, 4),
    ]:
        cfgs.append(
            triton.Config(
                {"BM": BM, "BN": BN, "BK": BK, "GROUP_M": group_m},
                num_warps=warps,
                num_stages=stages,
            )
        )
    return cfgs


@triton.autotune(
    configs=_configs(),
    key=["M", "N", "K"],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    OUT_DTYPE: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BK: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BM)
    grid_n = tl.cdiv(N, BN)

    group_size = GROUP_M
    pid_group = pid // (group_size * grid_n)
    first_pid_m = pid_group * group_size
    group_m = tl.minimum(grid_m - first_pid_m, group_size)
    pid_in_group = pid % (group_size * grid_n)
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    offs_k = tl.arange(0, BK)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BM, BN), dtype=tl.float32)

    k = 0
    while k < K:
        k_offsets = k + offs_k
        a = tl.load(
            a_ptrs,
            mask=(offs_m[:, None] < M) & (k_offsets[None, :] < K),
            other=0.0,
        )
        b = tl.load(
            b_ptrs,
            mask=(k_offsets[:, None] < K) & (offs_n[None, :] < N),
            other=0.0,
        )
        acc += tl.dot(a, b)
        k += BK
        a_ptrs += BK * stride_ak
        b_ptrs += BK * stride_bk

    acc = gelu(acc)
    out = acc.to(OUT_DTYPE)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (a.is_cuda and b.is_cuda):
        c = a @ b
        return torch.nn.functional.gelu(c)

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError(f"Incompatible shapes: a is {a.shape}, b is {b.shape}")

    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    if a.dtype not in (torch.float16, torch.bfloat16):
        a = a.to(torch.float16)
        b = b.to(torch.float16)

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda META: (triton.cdiv(M, META["BM"]) * triton.cdiv(N, META["BN"]),)

    out_dtype = tl.float16 if c.dtype == torch.float16 else tl.bfloat16

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
        OUT_DTYPE=out_dtype,
    )
    return c


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def gelu(x):
        return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

    def _configs():
        cfgs = []
        for BM, BN, BK, warps, stages, group_m in [
            (128, 128, 32, 8, 4, 8),
            (128, 64, 32, 4, 4, 8),
            (64, 128, 32, 4, 4, 8),
            (64, 64, 32, 4, 4, 8),
            (128, 128, 64, 8, 5, 8),
            (128, 64, 64, 4, 5, 8),
            (64, 128, 64, 4, 5, 8),
            (64, 64, 64, 4, 5, 8),
            (256, 64, 32, 8, 4, 4),
            (64, 256, 32, 8, 4, 4),
            (256, 128, 32, 8, 4, 4),
            (128, 256, 32, 8, 4, 4),
            (128, 128, 128, 8, 6, 4),
            (128, 64, 128, 4, 6, 4),
            (64, 128, 128, 4, 6, 4),
        ]:
            cfgs.append(
                triton.Config(
                    {"BM": BM, "BN": BN, "BK": BK, "GROUP_M": group_m},
                    num_warps=warps,
                    num_stages=stages,
                )
            )
        return cfgs

    @triton.autotune(
        configs=_configs(),
        key=["M", "N", "K"],
    )
    @triton.jit
    def _matmul_gelu_kernel(
        a_ptr,
        b_ptr,
        c_ptr,
        M: tl.constexpr,
        N: tl.constexpr,
        K: tl.constexpr,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        OUT_DTYPE: tl.constexpr,
        BM: tl.constexpr,
        BN: tl.constexpr,
        BK: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(0)

        grid_m = tl.cdiv(M, BM)
        grid_n = tl.cdiv(N, BN)

        group_size = GROUP_M
        pid_group = pid // (group_size * grid_n)
        first_pid_m = pid_group * group_size
        group_m = tl.minimum(grid_m - first_pid_m, group_size)
        pid_in_group = pid % (group_size * grid_n)
        pid_m = first_pid_m + (pid_in_group % group_m)
        pid_n = pid_in_group // group_m

        offs_m = pid_m * BM + tl.arange(0, BM)
        offs_n = pid_n * BN + tl.arange(0, BN)
        offs_k = tl.arange(0, BK)

        a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
        b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        acc = tl.zeros((BM, BN), dtype=tl.float32)

        k = 0
        while k < K:
            k_offsets = k + offs_k
            a = tl.load(
                a_ptrs,
                mask=(offs_m[:, None] < M) & (k_offsets[None, :] < K),
                other=0.0,
            )
            b = tl.load(
                b_ptrs,
                mask=(k_offsets[:, None] < K) & (offs_n[None, :] < N),
                other=0.0,
            )
            acc += tl.dot(a, b)
            k += BK
            a_ptrs += BK * stride_ak
            b_ptrs += BK * stride_bk

        acc = gelu(acc)
        out = acc.to(OUT_DTYPE)

        c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
        tl.store(c_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if not (a.is_cuda and b.is_cuda):
            c = a @ b
            return torch.nn.functional.gelu(c)

        if a.ndim != 2 or b.ndim != 2:
            raise ValueError("matmul expects 2D tensors")
        M, K = a.shape
        K2, N = b.shape
        if K2 != K:
            raise ValueError(f"Incompatible shapes: a is {a.shape}, b is {b.shape}")

        if a.dtype != b.dtype:
            b = b.to(a.dtype)

        if a.dtype not in (torch.float16, torch.bfloat16):
            a = a.to(torch.float16)
            b = b.to(torch.float16)

        c = torch.empty((M, N), device=a.device, dtype=a.dtype)

        grid = lambda META: (triton.cdiv(M, META["BM"]) * triton.cdiv(N, META["BN"]),)

        out_dtype = tl.float16 if c.dtype == torch.float16 else tl.bfloat16

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
            OUT_DTYPE=out_dtype,
        )
        return c
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
