import os
import sys
import textwrap

import torch
import triton
import triton.language as tl

KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_M: tl.constexpr, EVEN_N: tl.constexpr, EVEN_K: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(grid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group

    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    a_blk = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_blk = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, pid_n * BLOCK_N),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(1, 0),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        if EVEN_M and EVEN_K:
            a = tl.load(a_blk)
        else:
            a = tl.load(a_blk, boundary_check=(0, 1), padding_option='zero')

        if EVEN_N and EVEN_K:
            b = tl.load(b_blk)
        else:
            b = tl.load(b_blk, boundary_check=(0, 1), padding_option='zero')

        acc += tl.dot(a, b, out_dtype=tl.float32)

        a_blk = tl.advance(a_blk, (0, BLOCK_K))
        b_blk = tl.advance(b_blk, (BLOCK_K, 0))
        k += BLOCK_K

    acc = gelu(acc)
    out = acc.to(OUT_DTYPE)

    c_blk = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )

    if EVEN_M and EVEN_N:
        tl.store(c_blk, out)
    else:
        tl.store(c_blk, out, boundary_check=(0, 1))


def _select_meta(M: int, N: int, K: int):
    # Tile selection (favor 128 for general, adapt for skinny dimensions)
    if (N <= 512 and M >= 2048) or (N <= 512 and M >= N):
        BM, BN = 128, 64
    elif (M <= 512 and N >= 2048) or (M <= 512 and N >= M):
        BM, BN = 64, 128
    else:
        BM, BN = 128, 128

    # K tiling / pipelining
    if K <= 128:
        BK = 32
        num_stages = 3
    elif K >= 4096:
        BK = 128
        num_stages = 6
    elif K >= 2048:
        BK = 64
        num_stages = 5
    else:
        BK = 64
        num_stages = 4

    # Warps
    tile = BM * BN
    if tile >= 16384:
        num_warps = 8
    else:
        num_warps = 4

    GROUP_M = 8
    return BM, BN, BK, GROUP_M, num_warps, num_stages


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (a.is_cuda and b.is_cuda):
        x = a @ b
        return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")

    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError(f"incompatible shapes: {a.shape} x {b.shape}")

    if a.dtype != b.dtype:
        b = b.to(dtype=a.dtype)

    if a.dtype not in (torch.float16, torch.bfloat16):
        a = a.to(torch.float16)
        b = b.to(torch.float16)

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    BM, BN, BK, GROUP_M, num_warps, num_stages = _select_meta(M, N, K)

    even_m = (M % BM) == 0
    even_n = (N % BN) == 0
    even_k = (K % BK) == 0

    out_dtype = tl.float16 if a.dtype == torch.float16 else tl.bfloat16

    grid = (triton.cdiv(M, BM) * triton.cdiv(N, BN),)

    _matmul_gelu_kernel[grid](
        a, b, c,
        M=M, N=N, K=K,
        stride_am=a.stride(0), stride_ak=a.stride(1),
        stride_bk=b.stride(0), stride_bn=b.stride(1),
        stride_cm=c.stride(0), stride_cn=c.stride(1),
        BLOCK_M=BM, BLOCK_N=BN, BLOCK_K=BK,
        GROUP_M=GROUP_M,
        EVEN_M=even_m, EVEN_N=even_n, EVEN_K=even_k,
        OUT_DTYPE=out_dtype,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return c
'''

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
