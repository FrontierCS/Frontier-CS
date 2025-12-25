import os
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


configs = [
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32},
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32},
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32},
        num_stages=4,
        num_warps=4,
    ),
]


@triton.autotune(configs=configs, key=['M', 'N', 'K'])
@triton.jit
def _matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    DTYPE: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for _ in range(0, K, BLOCK_K):
        k_mask = offs_k[None, :] < K
        a = tl.load(
            a_ptrs,
            mask=(offs_m[:, None] < M) & k_mask,
            other=0.0,
        )
        b = tl.load(
            b_ptrs,
            mask=k_mask.T & (offs_n[None, :] < N),
            other=0.0,
        )
        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        offs_k += BLOCK_K

    acc = gelu(acc)

    acc = tl.cast(acc, DTYPE)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Input tensors must be 2D (matrices)")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible matrix shapes for multiplication")

    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb

    if M == 0 or N == 0 or K == 0:
        out_dtype = torch.promote_types(a.dtype, b.dtype)
        return torch.empty((M, N), device=a.device if a.is_cuda else b.device, dtype=out_dtype)

    if not (a.is_cuda and b.is_cuda):
        return torch.nn.functional.gelu(a @ b)

    if a.dtype != b.dtype:
        out_dtype = torch.promote_types(a.dtype, b.dtype)
        a_mat = a.to(out_dtype)
        b_mat = b.to(out_dtype)
    else:
        out_dtype = a.dtype
        a_mat = a
        b_mat = b

    if out_dtype == torch.float16:
        tl_dtype = tl.float16
    elif out_dtype == torch.bfloat16:
        tl_dtype = tl.bfloat16
    elif out_dtype == torch.float32:
        tl_dtype = tl.float32
    else:
        return torch.nn.functional.gelu(a @ b)

    c = torch.empty((M, N), device=a_mat.device, dtype=out_dtype)

    stride_am, stride_ak = a_mat.stride()
    stride_bk, stride_bn = b_mat.stride()
    stride_cm, stride_cn = c.stride()

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )

    _matmul_kernel[grid](
        a_mat, b_mat, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        DTYPE=tl_dtype,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
