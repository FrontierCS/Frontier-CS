import os
import math
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _bucket_small_dim(x: int) -> int:
    if x <= 64:
        return 0
    if x <= 128:
        return 1
    return 2


def _bucket_k(k: int) -> int:
    if k <= 512:
        return 0
    if k <= 1024:
        return 1
    return 2


def _get_autotune_configs():
    cfgs = []
    # Tall/skinny leaning (large M, small N)
    cfgs.append(triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4))
    cfgs.append(triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4))
    cfgs.append(triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=5))
    cfgs.append(triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4))
    # Short/wide leaning (small M, large N)
    cfgs.append(triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 1}, num_warps=8, num_stages=4))
    cfgs.append(triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 1}, num_warps=4, num_stages=4))
    # Small-ish fallback
    cfgs.append(triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=3))
    return cfgs


@triton.autotune(configs=_get_autotune_configs(), key=["ORIENT", "SBUCKET", "KCAT"])
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    ORIENT,
    SBUCKET,
    KCAT,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    pid_group = pid // (group_size * num_pid_n)
    first_pid_m = pid_group * group_size
    pid_in_group = pid % (group_size * num_pid_n)
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    a_block_ptr = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_block_ptr = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, pid_n * BLOCK_N),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iters = K // BLOCK_K
    for _ in tl.static_range(0, k_iters):
        a = tl.load(a_block_ptr, boundary_check=(0,), padding_option="zero")
        b = tl.load(b_block_ptr, boundary_check=(1,), padding_option="zero")
        acc += tl.dot(a, b)
        a_block_ptr = tl.advance(a_block_ptr, (0, BLOCK_K))
        b_block_ptr = tl.advance(b_block_ptr, (BLOCK_K, 0))

    acc = gelu(acc)

    c_block_ptr = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    tl.store(c_block_ptr, acc, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not isinstance(a, torch.Tensor) or not isinstance(b, torch.Tensor):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes: a is (M,K), b is (K,N)")
    if not a.is_cuda or not b.is_cuda:
        return torch.nn.functional.gelu(a @ b, approximate="none")
    if a.dtype not in (torch.float16, torch.bfloat16) or b.dtype != a.dtype:
        return torch.nn.functional.gelu(a @ b, approximate="none")

    M, K = a.shape
    _, N = b.shape

    if K % 32 != 0:
        return torch.nn.functional.gelu(a @ b, approximate="none")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    orient = 0 if M >= N else 1
    s_bucket = _bucket_small_dim(min(M, N))
    k_cat = _bucket_k(K)

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        stride_am=a.stride(0),
        stride_ak=a.stride(1),
        stride_bk=b.stride(0),
        stride_bn=b.stride(1),
        stride_cm=c.stride(0),
        stride_cn=c.stride(1),
        ORIENT=orient,
        SBUCKET=s_bucket,
        KCAT=k_cat,
        K=K,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}