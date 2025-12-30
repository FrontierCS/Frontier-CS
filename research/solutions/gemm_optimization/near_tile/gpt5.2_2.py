import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_autotune_configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
]


@triton.autotune(
    configs=_autotune_configs,
    key=["N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
)
@triton.heuristics(
    {
        "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
        "EVEN_M": lambda args: (args["M"] % args["BLOCK_M"]) == 0,
        "EVEN_N": lambda args: (args["N"] % args["BLOCK_N"]) == 0,
    }
)
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
    out_dtype: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * num_pid_in_group
    pid_n = pid_in_group % num_pid_n
    pid_m = first_pid_m + (pid_in_group // num_pid_n)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    if EVEN_M:
        a_mask_m = None
    else:
        a_mask_m = offs_m[:, None] < M

    if EVEN_N:
        b_mask_n = None
    else:
        b_mask_n = offs_n[None, :] < N

    k = 0
    while k < K:
        if EVEN_K:
            if a_mask_m is None:
                a = tl.load(a_ptrs, cache_modifier=".ca")
            else:
                a = tl.load(a_ptrs, mask=a_mask_m, other=0.0, cache_modifier=".ca")

            if b_mask_n is None:
                b = tl.load(b_ptrs, cache_modifier=".ca")
            else:
                b = tl.load(b_ptrs, mask=b_mask_n, other=0.0, cache_modifier=".ca")
        else:
            k_mask = (k + offs_k) < K
            if a_mask_m is None:
                a = tl.load(a_ptrs, mask=k_mask[None, :], other=0.0, cache_modifier=".ca")
            else:
                a = tl.load(a_ptrs, mask=a_mask_m & k_mask[None, :], other=0.0, cache_modifier=".ca")

            if b_mask_n is None:
                b = tl.load(b_ptrs, mask=k_mask[:, None], other=0.0, cache_modifier=".ca")
            else:
                b = tl.load(b_ptrs, mask=b_mask_n & k_mask[:, None], other=0.0, cache_modifier=".ca")

        acc += tl.dot(a, b)

        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c = acc.to(out_dtype)
    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    if EVEN_M and EVEN_N:
        tl.store(c_ptrs, c)
    else:
        mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(c_ptrs, c, mask=mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: a={tuple(a.shape)} b={tuple(b.shape)}")
    if not a.is_cuda or not b.is_cuda:
        x = a @ b
        return torch.nn.functional.gelu(x, approximate="none")
    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    M, K = a.shape
    _, N = b.shape

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    if a.dtype == torch.float16:
        out_tl = tl.float16
    elif a.dtype == torch.bfloat16:
        out_tl = tl.bfloat16
    elif a.dtype == torch.float32:
        out_tl = tl.float32
    else:
        raise TypeError(f"unsupported dtype: {a.dtype}")

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        K,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        out_dtype=out_tl,
    )
    return c


_KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

_autotune_configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
]

@triton.autotune(
    configs=_autotune_configs,
    key=["N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
)
@triton.heuristics(
    {
        "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
        "EVEN_M": lambda args: (args["M"] % args["BLOCK_M"]) == 0,
        "EVEN_N": lambda args: (args["N"] % args["BLOCK_N"]) == 0,
    }
)
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
    out_dtype: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * num_pid_in_group
    pid_n = pid_in_group % num_pid_n
    pid_m = first_pid_m + (pid_in_group // num_pid_n)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    if EVEN_M:
        a_mask_m = None
    else:
        a_mask_m = offs_m[:, None] < M

    if EVEN_N:
        b_mask_n = None
    else:
        b_mask_n = offs_n[None, :] < N

    k = 0
    while k < K:
        if EVEN_K:
            if a_mask_m is None:
                a = tl.load(a_ptrs, cache_modifier=".ca")
            else:
                a = tl.load(a_ptrs, mask=a_mask_m, other=0.0, cache_modifier=".ca")

            if b_mask_n is None:
                b = tl.load(b_ptrs, cache_modifier=".ca")
            else:
                b = tl.load(b_ptrs, mask=b_mask_n, other=0.0, cache_modifier=".ca")
        else:
            k_mask = (k + offs_k) < K
            if a_mask_m is None:
                a = tl.load(a_ptrs, mask=k_mask[None, :], other=0.0, cache_modifier=".ca")
            else:
                a = tl.load(a_ptrs, mask=a_mask_m & k_mask[None, :], other=0.0, cache_modifier=".ca")

            if b_mask_n is None:
                b = tl.load(b_ptrs, mask=k_mask[:, None], other=0.0, cache_modifier=".ca")
            else:
                b = tl.load(b_ptrs, mask=b_mask_n & k_mask[:, None], other=0.0, cache_modifier=".ca")

        acc += tl.dot(a, b)

        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)
    c = acc.to(out_dtype)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    if EVEN_M and EVEN_N:
        tl.store(c_ptrs, c)
    else:
        mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(c_ptrs, c, mask=mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")
    if not a.is_cuda or not b.is_cuda:
        x = a @ b
        return torch.nn.functional.gelu(x, approximate="none")
    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    M, K = a.shape
    _, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    if a.dtype == torch.float16:
        out_tl = tl.float16
    elif a.dtype == torch.bfloat16:
        out_tl = tl.bfloat16
    elif a.dtype == torch.float32:
        out_tl = tl.float32
    else:
        raise TypeError(f"unsupported dtype: {a.dtype}")

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        K,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        out_dtype=out_tl,
    )
    return c
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}