import torch
import triton
import triton.language as tl
import inspect
import sys


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32},
            num_stages=3,
            num_warps=8,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32},
            num_stages=4,
            num_warps=8,
        ),
        triton.Config(
            {"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32},
            num_stages=4,
            num_warps=8,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32},
            num_stages=4,
            num_warps=4,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32},
            num_stages=4,
            num_warps=4,
        ),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _matmul_kernel(
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
    DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    num_k_tiles = (K + BLOCK_K - 1) // BLOCK_K

    for k in range(0, num_k_tiles):
        offs_k = k * BLOCK_K + tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + (
            offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        )
        b_ptrs = b_ptr + (
            offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn
        )

        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

    acc = gelu(acc)

    c_ptrs = c_ptr + (
        offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    )
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    if DTYPE == 0:
        acc_out = acc.to(tl.float16)
    elif DTYPE == 1:
        acc_out = acc
    elif DTYPE == 2:
        acc_out = acc.to(tl.bfloat16)
    else:
        acc_out = acc

    tl.store(c_ptrs, acc_out, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Input tensors must be 2D")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible matrix shapes for multiplication")
    if a.device.type != "cuda" or b.device.type != "cuda":
        raise ValueError("Input tensors must be on CUDA device")
    if a.dtype != b.dtype:
        raise TypeError("Input tensors must have the same dtype")

    M, K = a.shape
    K2, N = b.shape
    assert K == K2

    if a.dtype == torch.float16:
        dtype_id = 0
    elif a.dtype == torch.float32:
        dtype_id = 1
    elif a.dtype == torch.bfloat16:
        dtype_id = 2
    else:
        raise TypeError(
            f"Unsupported dtype {a.dtype}. Supported: float16, float32, bfloat16."
        )

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    def grid(meta):
        return (
            triton.cdiv(M, meta["BLOCK_M"]),
            triton.cdiv(N, meta["BLOCK_N"]),
        )

    _matmul_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        K,
        a.stride(0),
        a.stride(1),
        b.stride(0),
        b.stride(1),
        c.stride(0),
        c.stride(1),
        DTYPE=dtype_id,
    )

    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if "__file__" in globals():
            return {"program_path": __file__}
        else:
            return {"code": inspect.getsource(sys.modules[__name__])}