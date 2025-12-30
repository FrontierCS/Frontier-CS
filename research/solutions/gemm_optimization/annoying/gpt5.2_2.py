import os
import sys
import math
import inspect
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_output_dtype(a: torch.Tensor, b: torch.Tensor) -> torch.dtype:
    if a.dtype in (torch.float16, torch.bfloat16) and b.dtype == a.dtype:
        return a.dtype
    if a.dtype == torch.float32 and b.dtype == torch.float32:
        return torch.float32
    if a.dtype == torch.float16 and b.dtype == torch.float16:
        return torch.float16
    if a.dtype == torch.bfloat16 and b.dtype == torch.bfloat16:
        return torch.bfloat16
    return torch.float32


def _get_tl_dtype(dtype: torch.dtype):
    if dtype == torch.float16:
        return tl.float16
    if dtype == torch.bfloat16:
        return tl.bfloat16
    return tl.float32


_MATMUL_CONFIGS = [
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=5,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=5,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=5,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8},
        num_warps=8,
        num_stages=6,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
        num_warps=4,
        num_stages=6,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8},
        num_warps=4,
        num_stages=6,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
        num_warps=4,
        num_stages=5,
    ),
    triton.Config(
        {"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 32, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=2,
        num_stages=4,
    ),
]


@triton.autotune(
    configs=_MATMUL_CONFIGS,
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * grid_n
    pid_group = pid // group_size
    first_pid_m = pid_group * GROUP_M
    pid_in_group = pid - pid_group * group_size
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

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

    # Hints for better codegen on typical contiguous inputs
    tl.multiple_of(stride_ak, 1)
    tl.multiple_of(stride_bn, 1)

    for _k in range(0, K, BLOCK_K):
        a = tl.load(a_blk, boundary_check=(0, 1), padding_option="zero")
        b = tl.load(b_blk, boundary_check=(0, 1), padding_option="zero")
        acc = tl.dot(a, b, acc=acc)
        a_blk = tl.advance(a_blk, (0, BLOCK_K))
        b_blk = tl.advance(b_blk, (BLOCK_K, 0))

    x = gelu(acc)

    if OUT_DTYPE == tl.float16:
        out = x.to(tl.float16)
    elif OUT_DTYPE == tl.bfloat16:
        out = x.to(tl.bfloat16)
    else:
        out = x.to(tl.float32)

    c_blk = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    tl.store(c_blk, out, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: a={tuple(a.shape)} b={tuple(b.shape)}")
    if not (a.is_cuda and b.is_cuda):
        x = a @ b
        return torch.nn.functional.gelu(x, approximate="none")

    M, K = a.shape
    _, N = b.shape

    out_dtype = _get_output_dtype(a, b)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    out_tl_dtype = _get_tl_dtype(out_dtype)

    grid = (triton.cdiv(M, 64) * triton.cdiv(N, 64),)

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
        OUT_DTYPE=out_tl_dtype,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return {"code": f.read()}
        except Exception:
            pass

        try:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
        except Exception:
            # Minimal fallback
            return {"code": "import torch\nimport triton\nimport triton.language as tl\n\n@triton.jit\ndef gelu(x):\n    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))\n\ndef matmul(a, b):\n    x = a @ b\n    return torch.nn.functional.gelu(x, approximate='none')\n"}