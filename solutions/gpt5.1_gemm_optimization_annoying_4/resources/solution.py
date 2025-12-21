import os
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


matmul_autotune_configs = [
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32},
        num_stages=2,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32},
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32},
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64},
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64},
        num_stages=3,
        num_warps=8,
    ),
]


@triton.autotune(configs=matmul_autotune_configs, key=['M', 'N', 'K'])
@triton.jit
def _matmul_kernel_fp16(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    for k in range(0, K, BLOCK_K):
        k_mask = k + offs_k < K
        a = tl.load(
            a_ptrs,
            mask=(offs_m[:, None] < M) & k_mask[None, :],
            other=0.0,
        )
        b = tl.load(
            b_ptrs,
            mask=k_mask[:, None] & (offs_n[None, :] < N),
            other=0.0,
        )
        acc += tl.dot(a, b, out_dtype=tl.float32)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)
    acc_converted = acc.to(tl.float16)

    c_ptrs = C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc_converted, mask=mask_c)


@triton.autotune(configs=matmul_autotune_configs, key=['M', 'N', 'K'])
@triton.jit
def _matmul_kernel_fp32(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    for k in range(0, K, BLOCK_K):
        k_mask = k + offs_k < K
        a = tl.load(
            a_ptrs,
            mask=(offs_m[:, None] < M) & k_mask[None, :],
            other=0.0,
        )
        b = tl.load(
            b_ptrs,
            mask=k_mask[:, None] & (offs_n[None, :] < N),
            other=0.0,
        )
        acc += tl.dot(a, b, out_dtype=tl.float32)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=mask_c)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible matrix shapes")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")
    if a.device != b.device:
        raise ValueError("Inputs must be on the same device")

    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb

    # Ensure same dtype
    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    dtype = a.dtype
    device = a.device

    if dtype == torch.float16:
        c = torch.empty((M, N), device=device, dtype=torch.float16)
        grid = lambda META: (
            triton.cdiv(M, META['BLOCK_M']),
            triton.cdiv(N, META['BLOCK_N']),
        )
        _matmul_kernel_fp16[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
        )
        return c

    if dtype == torch.float32:
        c = torch.empty((M, N), device=device, dtype=torch.float32)
        grid = lambda META: (
            triton.cdiv(M, META['BLOCK_M']),
            triton.cdiv(N, META['BLOCK_N']),
        )
        _matmul_kernel_fp32[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
        )
        return c

    # Fallback for unsupported dtypes: compute in float32 then cast back
    a_fp32 = a.to(torch.float32)
    b_fp32 = b.to(torch.float32)
    c_fp32 = torch.empty((M, N), device=device, dtype=torch.float32)
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    _matmul_kernel_fp32[grid](
        a_fp32, b_fp32, c_fp32,
        M, N, K,
        a_fp32.stride(0), a_fp32.stride(1),
        b_fp32.stride(0), b_fp32.stride(1),
        c_fp32.stride(0), c_fp32.stride(1),
    )
    return c_fp32.to(dtype)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(inspect.getfile(inspect.currentframe()))}
