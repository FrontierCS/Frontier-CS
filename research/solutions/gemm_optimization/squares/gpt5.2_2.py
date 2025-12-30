import os
import sys
import inspect
import math
from typing import Dict, Any, Optional

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_AUTOTUNE_CONFIGS = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=3),
]


@triton.autotune(
    configs=_AUTOTUNE_CONFIGS,
    key=["M", "N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
    warmup=1,
    rep=10,
)
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
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ak: tl.constexpr,
    stride_bk: tl.constexpr,
    stride_bn: tl.constexpr,
    stride_cm: tl.constexpr,
    stride_cn: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
    ALLOW_TF32: tl.constexpr,
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

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    if pid_m >= num_pid_m:
        return

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

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
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        if EVEN_M and EVEN_K:
            a = tl.load(a_blk)
        else:
            a = tl.load(a_blk, boundary_check=(0, 1), padding_option="zero")

        if EVEN_N and EVEN_K:
            b = tl.load(b_blk)
        else:
            b = tl.load(b_blk, boundary_check=(0, 1), padding_option="zero")

        acc += tl.dot(a, b, allow_tf32=ALLOW_TF32)
        a_blk = tl.advance(a_blk, (0, BLOCK_K))
        b_blk = tl.advance(b_blk, (BLOCK_K, 0))
        k += BLOCK_K

    acc = gelu(acc)
    out = tl.cast(acc, OUT_DTYPE)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    if EVEN_M and EVEN_N:
        tl.store(c_ptrs, out)
    else:
        mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(c_ptrs, out, mask=mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not a.is_cuda or not b.is_cuda:
        c = a @ b
        return torch.nn.functional.gelu(c, approximate="none")

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")

    M, K = a.shape
    K2, N = b.shape
    if K != K2:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)} b={tuple(b.shape)}")

    if a.dtype != b.dtype:
        b = b.to(dtype=a.dtype)

    if a.dtype == torch.float16:
        out_dtype = tl.float16
    elif a.dtype == torch.bfloat16:
        out_dtype = tl.bfloat16
    elif a.dtype == torch.float32:
        out_dtype = tl.float32
    else:
        a = a.to(torch.float16)
        b = b.to(torch.float16)
        out_dtype = tl.float16

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    allow_tf32 = bool(a.dtype == torch.float32 and torch.backends.cuda.matmul.allow_tf32)

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
        OUT_DTYPE=out_dtype,
        ALLOW_TF32=allow_tf32,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except Exception:
            pass
        src = inspect.getsource(sys.modules[__name__])
        return {"code": src}