import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    # Grouped ordering for better L2 locality
    group_size = GROUP_M
    num_pid_in_group = group_size * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    if pid_m >= grid_m:
        return

    offs_m = pid_m * BLOCK_M
    offs_n = pid_n * BLOCK_N

    a_blk = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(offs_m, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_blk = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, offs_n),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        tl.multiple_of(K, BLOCK_K)

    for _k in range(0, K, BLOCK_K):
        if EVEN_M and EVEN_K:
            a = tl.load(a_blk)
        else:
            a = tl.load(a_blk, boundary_check=(0, 1))
        if EVEN_N and EVEN_K:
            b = tl.load(b_blk)
        else:
            b = tl.load(b_blk, boundary_check=(0, 1))
        acc = tl.dot(a, b, out_dtype=tl.float32) + acc
        a_blk = tl.advance(a_blk, (0, BLOCK_K))
        b_blk = tl.advance(b_blk, (BLOCK_K, 0))

    acc = gelu(acc)

    c_blk = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )

    if EVEN_M and EVEN_N:
        tl.store(c_blk, acc)
    else:
        tl.store(c_blk, acc, boundary_check=(0, 1))


def _select_meta(M: int, N: int, K: int, dtype: torch.dtype):
    if dtype == torch.float32:
        BM, BN = 64, 64
        if K >= 128:
            BK = 64
            warps, stages = 4, 4
        else:
            BK = 32
            warps, stages = 4, 3
        group_m = 8
        return BM, BN, BK, warps, stages, group_m

    # fp16/bf16
    BM, BN = 128, 128
    if K >= 256:
        BK = 128
        warps, stages = 8, 3
    elif K >= 128:
        BK = 64
        warps, stages = 8, 4
    else:
        BK = 64
        warps, stages = 8, 4
    group_m = 8
    return BM, BN, BK, warps, stages, group_m


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors: a(M,K), b(K,N)")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("matmul expects CUDA tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")

    M, K = a.shape
    _, N = b.shape

    out_dtype = a.dtype if a.dtype == b.dtype else torch.result_type(a, b)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    BM, BN, BK, warps, stages, group_m = _select_meta(M, N, K, out_dtype)

    grid = (triton.cdiv(M, BM) * triton.cdiv(N, BN),)

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
        BLOCK_M=BM,
        BLOCK_N=BN,
        BLOCK_K=BK,
        GROUP_M=group_m,
        EVEN_M=(M % BM == 0),
        EVEN_N=(N % BN == 0),
        EVEN_K=(K % BK == 0),
        num_warps=warps,
        num_stages=stages,
    )
    return c


_SOLUTION_CODE = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    num_pid_in_group = group_size * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    if pid_m >= grid_m:
        return

    offs_m = pid_m * BLOCK_M
    offs_n = pid_n * BLOCK_N

    a_blk = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(offs_m, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_blk = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, offs_n),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        tl.multiple_of(K, BLOCK_K)

    for _k in range(0, K, BLOCK_K):
        if EVEN_M and EVEN_K:
            a = tl.load(a_blk)
        else:
            a = tl.load(a_blk, boundary_check=(0, 1))
        if EVEN_N and EVEN_K:
            b = tl.load(b_blk)
        else:
            b = tl.load(b_blk, boundary_check=(0, 1))
        acc = tl.dot(a, b, out_dtype=tl.float32) + acc
        a_blk = tl.advance(a_blk, (0, BLOCK_K))
        b_blk = tl.advance(b_blk, (BLOCK_K, 0))

    acc = gelu(acc)

    c_blk = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )

    if EVEN_M and EVEN_N:
        tl.store(c_blk, acc)
    else:
        tl.store(c_blk, acc, boundary_check=(0, 1))


def _select_meta(M: int, N: int, K: int, dtype: torch.dtype):
    if dtype == torch.float32:
        BM, BN = 64, 64
        if K >= 128:
            BK = 64
            warps, stages = 4, 4
        else:
            BK = 32
            warps, stages = 4, 3
        group_m = 8
        return BM, BN, BK, warps, stages, group_m

    BM, BN = 128, 128
    if K >= 256:
        BK = 128
        warps, stages = 8, 3
    elif K >= 128:
        BK = 64
        warps, stages = 8, 4
    else:
        BK = 64
        warps, stages = 8, 4
    group_m = 8
    return BM, BN, BK, warps, stages, group_m


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors: a(M,K), b(K,N)")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("matmul expects CUDA tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")

    M, K = a.shape
    _, N = b.shape

    out_dtype = a.dtype if a.dtype == b.dtype else torch.result_type(a, b)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    BM, BN, BK, warps, stages, group_m = _select_meta(M, N, K, out_dtype)

    grid = (triton.cdiv(M, BM) * triton.cdiv(N, BN),)

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
        BLOCK_M=BM,
        BLOCK_N=BN,
        BLOCK_K=BK,
        GROUP_M=group_m,
        EVEN_M=(M % BM == 0),
        EVEN_N=(N % BN == 0),
        EVEN_K=(K % BK == 0),
        num_warps=warps,
        num_stages=stages,
    )
    return c
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _SOLUTION_CODE}