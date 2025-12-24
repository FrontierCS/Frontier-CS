import os
import math
import textwrap
import inspect
import torch
import triton
import triton.language as tl

_KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

_AUTOTUNE_CONFIGS = [
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=3,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=3,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 32, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=3,
    ),
]

@triton.autotune(
    configs=_AUTOTUNE_CONFIGS,
    key=["M", "N", "K"],
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr, B_ptr, C_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_am: tl.constexpr, stride_ak: tl.constexpr,
    stride_bk: tl.constexpr, stride_bn: tl.constexpr,
    stride_cm: tl.constexpr, stride_cn: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    pid_group = pid // (GROUP_M * num_pid_n)
    first_pid_m = pid_group * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % (GROUP_M * num_pid_n)
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    for _ in range(0, tl.cdiv(K, BLOCK_K)):
        k_mask = (k + offs_k) < K
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (k_mask[None, :]), other=0.0)
        b = tl.load(b_ptrs, mask=(k_mask[:, None]) & (offs_n[None, :] < N), other=0.0)
        acc = tl.dot(a, b, acc)
        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(OUT_DTYPE), mask=mask_c)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensors")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")
    if not a.is_cuda or not b.is_cuda:
        import torch.nn.functional as F
        return F.gelu(a @ b)

    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    if a.dtype not in (torch.float16, torch.bfloat16):
        import torch.nn.functional as F
        return F.gelu(a @ b)

    M, K = a.shape
    _, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    out_dtype = tl.float16 if a.dtype == torch.float16 else tl.bfloat16

    _matmul_gelu_kernel[grid](
        a, b, c,
        M=M, N=N, K=K,
        stride_am=a.stride(0), stride_ak=a.stride(1),
        stride_bk=b.stride(0), stride_bn=b.stride(1),
        stride_cm=c.stride(0), stride_cn=c.stride(1),
        OUT_DTYPE=out_dtype,
    )
    return c
'''

exec(_KERNEL_CODE, globals(), globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
