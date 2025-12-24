import math
import os
from textwrap import dedent

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_id = pid // (GROUP_M * num_pid_n)
    first_pid_m = group_id * GROUP_M
    pid_m = first_pid_m + (pid % GROUP_M)
    pid_n = (pid // GROUP_M) % num_pid_n

    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    rm = tl.max_contiguous(rm, 1)
    rn = tl.max_contiguous(rn, 1)

    k_offsets = tl.arange(0, BLOCK_K)

    a_ptrs = A + rm[:, None] * stride_am + k_offsets[None, :] * stride_ak
    b_ptrs = B + k_offsets[:, None] * stride_bk + rn[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_tiles = tl.cdiv(K, BLOCK_K)
    for kt in range(0, k_tiles):
        k_curr = kt * BLOCK_K + k_offsets
        a_mask = (rm[:, None] < M) & (k_curr[None, :] < K)
        b_mask = (k_curr[:, None] < K) & (rn[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = C + rm[:, None] * stride_cm + rn[None, :] * stride_cn
    c_mask = (rm[:, None] < M) & (rn[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def _supports_triton_dtype(a: torch.dtype, b: torch.dtype) -> bool:
    supported = {torch.float16, torch.bfloat16}
    return (a in supported) and (b in supported)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D matrices"
    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb, "Inner dimensions must match"

    if not _supports_triton_dtype(a.dtype, b.dtype):
        return torch.nn.functional.gelu(a @ b)

    out_dtype = torch.promote_types(a.dtype, b.dtype)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = dedent(
            """
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _matmul_gelu_kernel(
                A, B, C,
                M, N, K,
                stride_am, stride_ak,
                stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)
                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)
                group_id = pid // (GROUP_M * num_pid_n)
                first_pid_m = group_id * GROUP_M
                pid_m = first_pid_m + (pid % GROUP_M)
                pid_n = (pid // GROUP_M) % num_pid_n

                rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                rm = tl.max_contiguous(rm, 1)
                rn = tl.max_contiguous(rn, 1)

                k_offsets = tl.arange(0, BLOCK_K)

                a_ptrs = A + rm[:, None] * stride_am + k_offsets[None, :] * stride_ak
                b_ptrs = B + k_offsets[:, None] * stride_bk + rn[None, :] * stride_bn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                k_tiles = tl.cdiv(K, BLOCK_K)
                for kt in range(0, k_tiles):
                    k_curr = kt * BLOCK_K + k_offsets
                    a_mask = (rm[:, None] < M) & (k_curr[None, :] < K)
                    b_mask = (k_curr[:, None] < K) & (rn[None, :] < N)
                    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                    acc += tl.dot(a, b)
                    a_ptrs += BLOCK_K * stride_ak
                    b_ptrs += BLOCK_K * stride_bk

                acc = gelu(acc)

                c_ptrs = C + rm[:, None] * stride_cm + rn[None, :] * stride_cn
                c_mask = (rm[:, None] < M) & (rn[None, :] < N)
                tl.store(c_ptrs, acc, mask=c_mask)

            def _supports_triton_dtype(a: torch.dtype, b: torch.dtype) -> bool:
                supported = {torch.float16, torch.bfloat16}
                return (a in supported) and (b in supported)

            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
                assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D matrices"
                M, K = a.shape
                Kb, N = b.shape
                assert K == Kb, "Inner dimensions must match"

                if not _supports_triton_dtype(a.dtype, b.dtype):
                    return torch.nn.functional.gelu(a @ b)

                out_dtype = torch.promote_types(a.dtype, b.dtype)
                c = torch.empty((M, N), device=a.device, dtype=out_dtype)

                grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

                _matmul_gelu_kernel[grid](
                    a, b, c,
                    M, N, K,
                    a.stride(0), a.stride(1),
                    b.stride(0), b.stride(1),
                    c.stride(0), c.stride(1),
                )
                return c
            """
        ).strip("\n")
        return {"code": code}
