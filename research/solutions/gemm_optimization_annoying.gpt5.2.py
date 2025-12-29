import os
import sys
import math
import inspect
from typing import Dict, Any, Optional

import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if tl is not None:

    @triton.jit
    def gelu(x):
        return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

    _MATMUL_CONFIGS = [
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
            {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=4,
            num_stages=5,
        ),
        triton.Config(
            {"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4},
            num_warps=8,
            num_stages=3,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4},
            num_warps=8,
            num_stages=3,
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
        pid = tl.program_id(axis=0)

        grid_m = tl.cdiv(M, BLOCK_M)
        grid_n = tl.cdiv(N, BLOCK_N)

        num_pid_in_group = GROUP_M * grid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_M
        group_size_m = tl.minimum(grid_m - first_pid_m, GROUP_M)
        pid_in_group = pid - group_id * num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
        b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        k = 0
        while k < K:
            k_mask = (k + offs_k) < K
            a = tl.load(
                a_ptrs,
                mask=(offs_m[:, None] < M) & (k_mask[None, :]),
                other=0.0,
            )
            b = tl.load(
                b_ptrs,
                mask=(k_mask[:, None]) & (offs_n[None, :] < N),
                other=0.0,
            )
            acc += tl.dot(a, b)

            k += BLOCK_K
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk

        acc = gelu(acc)

        if OUT_DTYPE == tl.float16:
            out = acc.to(tl.float16)
        elif OUT_DTYPE == tl.bfloat16:
            out = acc.to(tl.bfloat16)
        else:
            out = acc.to(tl.float32)

        c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
        tl.store(c_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def _torch_gelu_erf(x: torch.Tensor) -> torch.Tensor:
    return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Expected a and b to be 2D tensors with shapes (M, K) and (K, N).")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")

    M, K = a.shape
    K2, N = b.shape
    if M == 0 or N == 0 or K == 0:
        return torch.empty((M, N), device=a.device, dtype=a.dtype)

    if not a.is_cuda or triton is None:
        return _torch_gelu_erf(a @ b)

    if b.device != a.device:
        raise ValueError("a and b must be on the same device")

    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        a = a.to(torch.float16)
    if b.dtype != a.dtype:
        b = b.to(a.dtype)

    out_dtype = a.dtype
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    if tl is not None:
        if out_dtype == torch.float16:
            out_tl = tl.float16
        elif out_dtype == torch.bfloat16:
            out_tl = tl.bfloat16
        else:
            out_tl = tl.float32
    else:
        out_tl = None

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

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


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except Exception:
            pass
        try:
            src = None
            try:
                src = inspect.getsource(sys.modules[__name__])
            except Exception:
                src = None
            if src is None:
                raise RuntimeError("Unable to obtain source code")
            return {"code": src}
        except Exception:
            minimal = (
                "import torch\n"
                "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:\n"
                "    x = a @ b\n"
                "    return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))\n"
            )
            return {"code": minimal}