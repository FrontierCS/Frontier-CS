import math
import textwrap
from typing import Dict, Optional

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_triton_dtype(dtype: torch.dtype):
    if dtype == torch.float16:
        return tl.float16
    if dtype == torch.bfloat16:
        return tl.bfloat16
    if dtype == torch.float32:
        return tl.float32
    raise TypeError(f"Unsupported dtype: {dtype}")


def _configs():
    return [
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8},
            num_warps=8,
            num_stages=3,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
    ]


@triton.autotune(
    configs=_configs(),
    key=["K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm: tl.constexpr,
    stride_cn: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * num_pid_n
    group_id = pid // group_size
    first_pid_m = group_id * GROUP_M
    group_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid - group_id * group_size
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_remaining = K
    while k_remaining > 0:
        k_mask = offs_k < k_remaining
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
        acc += tl.dot(a, b, out_dtype=tl.float32)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_remaining -= BLOCK_K

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(OUT_DTYPE), mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")
    if a.dtype != b.dtype:
        raise ValueError(f"dtype mismatch: a.dtype={a.dtype}, b.dtype={b.dtype}")

    M, K = a.shape
    _, N = b.shape

    if not a.is_cuda or not b.is_cuda:
        out = a @ b
        return torch.nn.functional.gelu(out, approximate="none")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    out_tl = _get_triton_dtype(a.dtype)

    grid = (triton.cdiv(M, 128) * triton.cdiv(N, 128),)
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
        OUT_DTYPE=out_tl,
    )
    return c


_SOLUTION_CODE = textwrap.dedent(
    r"""
    import math
    import torch
    import triton
    import triton.language as tl


    @triton.jit
    def gelu(x):
        return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


    def _get_triton_dtype(dtype: torch.dtype):
        if dtype == torch.float16:
            return tl.float16
        if dtype == torch.bfloat16:
            return tl.bfloat16
        if dtype == torch.float32:
            return tl.float32
        raise TypeError(f"Unsupported dtype: {dtype}")


    def _configs():
        return [
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8, num_stages=3),
            triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
        ]


    @triton.autotune(
        configs=_configs(),
        key=["K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
    )
    @triton.jit
    def _matmul_gelu_kernel(
        a_ptr,
        b_ptr,
        c_ptr,
        M: tl.constexpr,
        N: tl.constexpr,
        K,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm: tl.constexpr,
        stride_cn: tl.constexpr,
        OUT_DTYPE: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(axis=0)

        num_pid_m = tl.cdiv(M, BLOCK_M)
        num_pid_n = tl.cdiv(N, BLOCK_N)

        group_size = GROUP_M * num_pid_n
        group_id = pid // group_size
        first_pid_m = group_id * GROUP_M
        group_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
        pid_in_group = pid - group_id * group_size
        pid_m = first_pid_m + (pid_in_group % group_m)
        pid_n = pid_in_group // group_m

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
        b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k_remaining = K
        while k_remaining > 0:
            k_mask = offs_k < k_remaining
            a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask[None, :], other=0.0)
            b = tl.load(b_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
            acc += tl.dot(a, b, out_dtype=tl.float32)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k_remaining -= BLOCK_K

        acc = gelu(acc)

        c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
        c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(c_ptrs, acc.to(OUT_DTYPE), mask=c_mask)


    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if a.ndim != 2 or b.ndim != 2:
            raise ValueError("matmul expects 2D tensors")
        if a.shape[1] != b.shape[0]:
            raise ValueError(f"Incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")
        if a.dtype != b.dtype:
            raise ValueError(f"dtype mismatch: a.dtype={a.dtype}, b.dtype={b.dtype}")

        M, K = a.shape
        _, N = b.shape

        if not a.is_cuda or not b.is_cuda:
            out = a @ b
            return torch.nn.functional.gelu(out, approximate="none")

        c = torch.empty((M, N), device=a.device, dtype=a.dtype)

        stride_am, stride_ak = a.stride()
        stride_bk, stride_bn = b.stride()
        stride_cm, stride_cn = c.stride()

        out_tl = _get_triton_dtype(a.dtype)

        grid = (triton.cdiv(M, 128) * triton.cdiv(N, 128),)
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
            OUT_DTYPE=out_tl,
        )
        return c
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _SOLUTION_CODE}
