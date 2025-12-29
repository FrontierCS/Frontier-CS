import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _to_tl_dtype(torch_dtype):
    if torch_dtype == torch.float16:
        return tl.float16
    if torch_dtype == torch.bfloat16:
        return tl.bfloat16
    return tl.float32


def _promote_torch_dtype(a_dtype, b_dtype):
    # Prefer keeping low-precision if both are low-precision
    if a_dtype == b_dtype:
        return a_dtype
    # Use torch's promotion for safety
    try:
        return torch.promote_types(a_dtype, b_dtype)
    except Exception:
        # Fallback
        if torch.float32 in (a_dtype, b_dtype):
            return torch.float32
        if torch.bfloat16 in (a_dtype, b_dtype):
            return torch.bfloat16
        return torch.float16


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=3, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4},
            num_stages=4, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 16, 'GROUP_M': 8},
            num_stages=3, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 16, 'GROUP_M': 4},
            num_stages=3, num_warps=2
        ),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    A_TYPE: tl.constexpr, B_TYPE: tl.constexpr, C_TYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    # group linearized
    num_groups = tl.cdiv(num_pid_m, group_size)
    group_id = pid // (num_pid_n * group_size)
    pid_in_group = pid % (num_pid_n * group_size)
    pid_m = group_id * group_size + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size
    pid_m = tl.minimum(pid_m, num_pid_m - 1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)
        b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(A_TYPE)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(B_TYPE)
        acc += tl.dot(a, b)
        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    # Cast to output dtype
    c = acc.to(C_TYPE)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    Args:
        a: shape (M, K)
        b: shape (K, N)
    Returns:
        shape (M, N) with GELU applied
    """
    if not (a.is_cuda and b.is_cuda):
        raise RuntimeError("Inputs must be CUDA tensors")
    if a.dim() != 2 or b.dim() != 2:
        raise RuntimeError("Inputs must be 2D matrices")
    M, K1 = a.shape
    K2, N = b.shape
    if K1 != K2:
        raise RuntimeError("Inner dimensions must match")

    # Promote dtypes if needed
    out_dtype = _promote_torch_dtype(a.dtype, b.dtype)
    a_mat = a.to(out_dtype)
    b_mat = b.to(out_dtype)

    # Ensure contiguous strides are properly handled
    a_stride_am, a_stride_ak = a_mat.stride()
    b_stride_bk, b_stride_bn = b_mat.stride()

    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)
    c_stride_cm, c_stride_cn = c.stride()

    # Triton expects ints
    M32 = int(M)
    N32 = int(N)
    K32 = int(K1)

    # Triton dtypes
    A_TYPE = _to_tl_dtype(a_mat.dtype)
    B_TYPE = _to_tl_dtype(b_mat.dtype)
    C_TYPE = _to_tl_dtype(c.dtype)

    def grid(meta):
        return (triton.cdiv(M32, meta['BLOCK_M']) * triton.cdiv(N32, meta['BLOCK_N']),)

    _matmul_gelu_kernel[grid](
        a_mat, b_mat, c,
        M32, N32, K32,
        a_stride_am, a_stride_ak,
        b_stride_bk, b_stride_bn,
        c_stride_cm, c_stride_cn,
        A_TYPE=A_TYPE, B_TYPE=B_TYPE, C_TYPE=C_TYPE,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _to_tl_dtype(torch_dtype):
    if torch_dtype == torch.float16:
        return tl.float16
    if torch_dtype == torch.bfloat16:
        return tl.bfloat16
    return tl.float32


def _promote_torch_dtype(a_dtype, b_dtype):
    try:
        return torch.promote_types(a_dtype, b_dtype)
    except Exception:
        if torch.float32 in (a_dtype, b_dtype):
            return torch.float32
        if torch.bfloat16 in (a_dtype, b_dtype):
            return torch.bfloat16
        return torch.float16


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=3, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4},
            num_stages=4, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=4, num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 16, 'GROUP_M': 8},
            num_stages=3, num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 16, 'GROUP_M': 4},
            num_stages=3, num_warps=2
        ),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    A_TYPE: tl.constexpr, B_TYPE: tl.constexpr, C_TYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    num_groups = tl.cdiv(num_pid_m, group_size)
    group_id = pid // (num_pid_n * group_size)
    pid_in_group = pid % (num_pid_n * group_size)
    pid_m = group_id * group_size + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size
    pid_m = tl.minimum(pid_m, num_pid_m - 1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)
        b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(A_TYPE)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(B_TYPE)
        acc += tl.dot(a, b)
        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)
    c = acc.to(C_TYPE)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (a.is_cuda and b.is_cuda):
        raise RuntimeError("Inputs must be CUDA tensors")
    if a.dim() != 2 or b.dim() != 2:
        raise RuntimeError("Inputs must be 2D matrices")
    M, K1 = a.shape
    K2, N = b.shape
    if K1 != K2:
        raise RuntimeError("Inner dimensions must match")

    out_dtype = torch.promote_types(a.dtype, b.dtype) if a.dtype != b.dtype else a.dtype
    a_mat = a.to(out_dtype)
    b_mat = b.to(out_dtype)

    a_stride_am, a_stride_ak = a_mat.stride()
    b_stride_bk, b_stride_bn = b_mat.stride()

    c = torch.empty((M, N), device=a.device, dtype=out_dtype)
    c_stride_cm, c_stride_cn = c.stride()

    M32 = int(M)
    N32 = int(N)
    K32 = int(K1)

    A_TYPE = _to_tl_dtype(a_mat.dtype)
    B_TYPE = _to_tl_dtype(b_mat.dtype)
    C_TYPE = _to_tl_dtype(c.dtype)

    def grid(meta):
        return (triton.cdiv(M32, meta['BLOCK_M']) * triton.cdiv(N32, meta['BLOCK_N']),)

    _matmul_gelu_kernel[grid](
        a_mat, b_mat, c,
        M32, N32, K32,
        a_stride_am, a_stride_ak,
        b_stride_bk, b_stride_bn,
        c_stride_cm, c_stride_cn,
        A_TYPE=A_TYPE, B_TYPE=B_TYPE, C_TYPE=C_TYPE,
    )
    return c
'''
        return {"code": code}