import os
import math
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

def _get_configs():
    return [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),

        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4, num_stages=5),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4, num_stages=5),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8, num_stages=5),
    ]

@triton.autotune(
    configs=_get_configs(),
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_am: tl.constexpr, stride_ak: tl.constexpr,
    stride_bk: tl.constexpr, stride_bn: tl.constexpr,
    stride_cm: tl.constexpr, stride_cn: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    tl.multiple_of(stride_ak, 1)
    tl.multiple_of(stride_bn, 1)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_remaining = K
    k_iter = 0
    while k_remaining > 0:
        k_mask = (k_iter * BLOCK_K + offs_k) < K
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

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_iter += 1
        k_remaining -= BLOCK_K

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, tl.cast(acc, OUT_DTYPE), mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (a.is_cuda and b.is_cuda):
        raise ValueError("Inputs must be CUDA tensors")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors")
    M, K = a.shape
    K2, N = b.shape
    if K != K2:
        raise ValueError(f"Incompatible shapes: {a.shape} x {b.shape}")

    if a.dtype in (torch.float16, torch.bfloat16):
        out_dtype = a.dtype
    elif a.dtype == torch.float32:
        out_dtype = torch.float32
    else:
        raise ValueError(f"Unsupported dtype: {a.dtype}")

    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    if out_dtype == torch.float16:
        out_tl = tl.float16
    elif out_dtype == torch.bfloat16:
        out_tl = tl.bfloat16
    else:
        out_tl = tl.float32

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    _matmul_gelu_kernel[grid](
        a, b, c,
        M=M, N=N, K=K,
        stride_am=stride_am, stride_ak=stride_ak,
        stride_bk=stride_bk, stride_bn=stride_bn,
        stride_cm=stride_cm, stride_cn=stride_cn,
        OUT_DTYPE=out_tl,
    )
    return c
'''

# Define matmul in this module namespace as a convenience (some harnesses import directly)
_exec_globals = {}
exec(KERNEL_CODE, _exec_globals)
matmul = _exec_globals["matmul"]
gelu = _exec_globals["gelu"]

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
