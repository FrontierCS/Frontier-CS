import typing


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 32,  "GROUP_M": 8}, num_warps=4,  num_stages=3),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32,  "GROUP_M": 8}, num_warps=4,  num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32,  "GROUP_M": 8}, num_warps=4,  num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32,  "GROUP_M": 8}, num_warps=8,  num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64,  "GROUP_M": 8}, num_warps=8,  num_stages=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 64,  "GROUP_M": 8}, num_warps=4,  num_stages=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 64,  "GROUP_M": 8}, num_warps=8,  num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 64,  "GROUP_M": 8}, num_warps=8,  num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8,  num_stages=5),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64,  "BLOCK_K": 64,  "GROUP_M": 4}, num_warps=8,  num_stages=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 64,  "GROUP_M": 4}, num_warps=8,  num_stages=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 64,  "GROUP_M": 4}, num_warps=16, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 64,  "GROUP_M": 4}, num_warps=16, num_stages=4),
    ],
    key=[
        "M", "N", "K",
        "a_stride_am", "a_stride_ak",
        "b_stride_bk", "b_stride_bn",
        "c_stride_cm", "c_stride_cn"
    ],
)
@triton.jit
def _matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    a_stride_am, a_stride_ak,
    b_stride_bk, b_stride_bn,
    c_stride_cm, c_stride_cn,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A + (offs_m[:, None] * a_stride_am + offs_k[None, :] * a_stride_ak)
    b_ptrs = B + (offs_k[:, None] * b_stride_bk + offs_n[None, :] * b_stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)
        b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        k += BLOCK_K
        a_ptrs += BLOCK_K * a_stride_ak
        b_ptrs += BLOCK_K * b_stride_bk

    # Apply GELU activation in float32 for precision
    acc = gelu(acc)

    c_ptrs = C + (offs_m[:, None] * c_stride_cm + offs_n[None, :] * c_stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    out = acc.to(OUT_DTYPE)
    tl.store(c_ptrs, out, mask=c_mask)


def _torch_dtype_to_triton(dtype: torch.dtype):
    if dtype == torch.float16:
        return tl.float16
    if dtype == torch.bfloat16:
        return tl.bfloat16
    if dtype == torch.float32:
        return tl.float32
    # Fallback: cast unsupported dtypes to float32 in kernel
    return tl.float32


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    Args:
        a: Tensor of shape (M, K) on CUDA
        b: Tensor of shape (K, N) on CUDA
    Returns:
        Tensor of shape (M, N) with GELU applied, same dtype as a
    """
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D matrices"
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2, "Inner dimensions must match"
    # Use dtype of 'a' for output, as commonly expected
    assert a.dtype in (torch.float16, torch.bfloat16, torch.float32), "Unsupported dtype for 'a'"
    assert b.dtype in (torch.float16, torch.bfloat16, torch.float32), "Unsupported dtype for 'b'"
    # It's typical to require a and b have same dtype for high-performance kernels
    # but to be permissive cast b to a.dtype if different.
    if b.dtype != a.dtype:
        b = b.to(a.dtype)

    M = int(M)
    N = int(N)
    K = int(K1)

    out = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"]),
        triton.cdiv(N, META["BLOCK_N"]),
    )

    _matmul_gelu_kernel[grid](
        a, b, out,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        out.stride(0), out.stride(1),
        OUT_DTYPE=_torch_dtype_to_triton(out.dtype),
    )
    return out
'''
        return {"code": code}