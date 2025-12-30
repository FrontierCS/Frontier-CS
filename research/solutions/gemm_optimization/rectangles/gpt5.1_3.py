import os
import types
import torch
import triton
import triton.language as tl


# Ensure tl.extra.cuda.libdevice.erf exists as in the problem spec
if not hasattr(tl, "extra"):
    tl.extra = types.SimpleNamespace()
if not hasattr(tl.extra, "cuda"):
    tl.extra.cuda = types.SimpleNamespace()
if not hasattr(tl.extra.cuda, "libdevice"):
    tl.extra.cuda.libdevice = types.SimpleNamespace()
if not hasattr(tl.extra.cuda.libdevice, "erf"):
    # Fallback to standard Triton erf if available
    if hasattr(tl, "math") and hasattr(tl.math, "erf"):
        tl.extra.cuda.libdevice.erf = tl.math.erf
    elif hasattr(tl, "libdevice") and hasattr(tl.libdevice, "erf"):
        tl.extra.cuda.libdevice.erf = tl.libdevice.erf
    else:
        raise RuntimeError("Could not find an erf implementation in triton")


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config(
            {
                "BLOCK_M": 128,
                "BLOCK_N": 128,
                "BLOCK_K": 32,
                "GROUP_M": 8,
            },
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {
                "BLOCK_M": 128,
                "BLOCK_N": 64,
                "BLOCK_K": 32,
                "GROUP_M": 8,
            },
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 128,
                "BLOCK_K": 32,
                "GROUP_M": 8,
            },
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 64,
                "BLOCK_K": 32,
                "GROUP_M": 8,
            },
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {
                "BLOCK_M": 256,
                "BLOCK_N": 64,
                "BLOCK_K": 32,
                "GROUP_M": 4,
            },
            num_stages=4,
            num_warps=8,
        ),
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 256,
                "BLOCK_K": 32,
                "GROUP_M": 4,
            },
            num_stages=4,
            num_warps=8,
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * num_pid_n
    group_id = pid // group_size
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % group_size
    pid_m = first_pid_m + pid_in_group // num_pid_n
    pid_n = pid_in_group % num_pid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = tl.cdiv(K, BLOCK_K)
    for _ in range(0, k_iter):
        k_mask = offs_k[None, :] < K
        a_mask = (offs_m[:, None] < M) & k_mask
        b_mask = k_mask.T & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        offs_k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D tensors"
    assert a.shape[1] == b.shape[0], "Incompatible matrix shapes"
    assert a.device.type == "cuda" and b.device.type == "cuda", "Inputs must be on CUDA device"
    assert a.device == b.device, "Inputs must be on the same device"

    M, K = a.shape
    Kb, N = b.shape
    del Kb

    if a.dtype != b.dtype or a.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        c = a @ b
        return c * 0.5 * (1.0 + torch.erf(c * 0.7071067811865476))

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),
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
    )

    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}