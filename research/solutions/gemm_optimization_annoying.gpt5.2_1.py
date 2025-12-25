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


def _gen_autotune_configs():
    cfgs = []
    for bm, bn, bk, warps, stages, gm in [
        (128, 128, 32, 8, 4, 8),
        (128, 64, 32, 8, 4, 8),
        (64, 128, 32, 8, 4, 8),
        (64, 64, 32, 4, 4, 8),
        (128, 128, 64, 8, 5, 8),
        (128, 64, 64, 8, 5, 8),
        (64, 128, 64, 8, 5, 8),
        (64, 64, 64, 4, 5, 8),
        (128, 256, 32, 8, 4, 4),
        (256, 128, 32, 8, 4, 4),
    ]:
        cfgs.append(
            triton.Config(
                {"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk, "GROUP_M": gm},
                num_warps=warps,
                num_stages=stages,
            )
        )
    return cfgs


@triton.autotune(configs=_gen_autotune_configs(), key=["M", "N", "K"])
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
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    m0 = pid_m * BLOCK_M
    n0 = pid_n * BLOCK_N

    offs_m = m0 + tl.arange(0, BLOCK_M)
    offs_n = n0 + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    k = 0
    tl.multiple_of(stride_ak, 1)
    tl.multiple_of(stride_bn, 1)

    for _ in tl.static_range(0, 1, 1):
        pass

    for k in range(0, K, BLOCK_K):
        k_mask = (k + offs_k) < K
        a = tl.load(a_ptrs, mask=((offs_m[:, None] < M) & (k_mask[None, :])), other=0.0)
        b = tl.load(b_ptrs, mask=((k_mask[:, None]) & (offs_n[None, :] < N)), other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, acc, mask=((offs_m[:, None] < M) & (offs_n[None, :] < N)))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: {tuple(a.shape)} x {tuple(b.shape)}")
    if a.device.type != "cuda" or b.device.type != "cuda":
        import torch.nn.functional as F

        return F.gelu(a @ b)

    if a.dtype != b.dtype:
        b = b.to(dtype=a.dtype)

    M, K = a.shape
    _, N = b.shape

    out_dtype = a.dtype if a.dtype in (torch.float16, torch.bfloat16, torch.float32) else torch.float16
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

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
        code = r'''
import math
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def _gen_autotune_configs():
    cfgs = []
    for bm, bn, bk, warps, stages, gm in [
        (128, 128, 32, 8, 4, 8),
        (128, 64, 32, 8, 4, 8),
        (64, 128, 32, 8, 4, 8),
        (64, 64, 32, 4, 4, 8),
        (128, 128, 64, 8, 5, 8),
        (128, 64, 64, 8, 5, 8),
        (64, 128, 64, 8, 5, 8),
        (64, 64, 64, 4, 5, 8),
        (128, 256, 32, 8, 4, 4),
        (256, 128, 32, 8, 4, 4),
    ]:
        cfgs.append(triton.Config(
            {"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk, "GROUP_M": gm},
            num_warps=warps,
            num_stages=stages
        ))
    return cfgs

@triton.autotune(configs=_gen_autotune_configs(), key=["M", "N", "K"])
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    m0 = pid_m * BLOCK_M
    n0 = pid_n * BLOCK_N

    offs_m = m0 + tl.arange(0, BLOCK_M)
    offs_n = n0 + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    for k in range(0, K, BLOCK_K):
        k_mask = (k + offs_k) < K
        a = tl.load(a_ptrs, mask=((offs_m[:, None] < M) & (k_mask[None, :])), other=0.0)
        b = tl.load(b_ptrs, mask=((k_mask[:, None]) & (offs_n[None, :] < N)), other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, acc, mask=((offs_m[:, None] < M) & (offs_n[None, :] < N)))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: {tuple(a.shape)} x {tuple(b.shape)}")
    if a.device.type != "cuda" or b.device.type != "cuda":
        import torch.nn.functional as F
        return F.gelu(a @ b)
    if a.dtype != b.dtype:
        b = b.to(dtype=a.dtype)

    M, K = a.shape
    _, N = b.shape
    out_dtype = a.dtype if a.dtype in (torch.float16, torch.bfloat16, torch.float32) else torch.float16
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)
    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c
'''
        return {"code": textwrap.dedent(code).lstrip()}
