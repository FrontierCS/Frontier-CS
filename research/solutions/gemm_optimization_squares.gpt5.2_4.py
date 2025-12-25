import os
import math
import inspect
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=8,
            num_stages=5,
        ),
        triton.Config(
            {"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
    ],
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_m = GROUP_M
    num_pid_in_group = group_m * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_m
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

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

    k = 0
    while k < K:
        a = tl.load(a_blk, boundary_check=(0, 1), padding_option="zero")
        b = tl.load(b_blk, boundary_check=(0, 1), padding_option="zero")
        acc += tl.dot(a, b)
        a_blk = tl.advance(a_blk, (0, BLOCK_K))
        b_blk = tl.advance(b_blk, (BLOCK_K, 0))
        k += BLOCK_K

    acc = gelu(acc)

    c_blk = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    tl.store(c_blk, acc.to(OUT_DTYPE), boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")
    if a.numel() == 0 or b.numel() == 0:
        return torch.empty((a.shape[0], b.shape[1]), device=a.device, dtype=a.dtype)

    if not (a.is_cuda and b.is_cuda):
        x = a @ b
        return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))

    if a.dtype not in (torch.float16, torch.bfloat16) or b.dtype not in (torch.float16, torch.bfloat16):
        x = a @ b
        return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))

    M, K = a.shape
    _, N = b.shape

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    out_tl_dtype = tl.float16 if c.dtype == torch.float16 else tl.bfloat16

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

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
        OUT_DTYPE=out_tl_dtype,
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

        parts = []
        parts.append("import torch\nimport triton\nimport triton.language as tl\n")
        parts.append(inspect.getsource(gelu) + "\n\n")
        parts.append(inspect.getsource(_matmul_gelu_kernel) + "\n\n")
        parts.append(inspect.getsource(matmul) + "\n")
        return {"code": "".join(parts)}
