import os
import sys
import inspect
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_autotune_configs():
    configs = []
    for bm, bn, bk, warps, stages, group_m in [
        (128, 128, 32, 8, 4, 8),
        (128, 256, 32, 8, 4, 8),
        (256, 128, 32, 8, 4, 8),
        (64, 256, 32, 8, 4, 8),
        (256, 64, 32, 8, 4, 8),
        (64, 128, 32, 4, 4, 8),
        (128, 64, 32, 4, 4, 8),
        (64, 64, 32, 4, 4, 8),
        (128, 128, 64, 8, 5, 8),
        (64, 128, 64, 4, 5, 8),
    ]:
        configs.append(
            triton.Config(
                {
                    "BLOCK_M": bm,
                    "BLOCK_N": bn,
                    "BLOCK_K": bk,
                    "GROUP_M": group_m,
                },
                num_warps=warps,
                num_stages=stages,
            )
        )
    return configs


@triton.autotune(
    configs=_get_autotune_configs(),
    key=["M", "N", "K", "OUT_DTYPE"],
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

    group_size = GROUP_M * grid_n
    pid_group = pid // group_size
    first_pid_m = pid_group * GROUP_M
    group_m = tl.minimum(grid_m - first_pid_m, GROUP_M)
    pid_in_group = pid - pid_group * group_size
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
        b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < K), other=0.0)
        b = tl.load(b_ptrs, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)

        acc += tl.dot(a, b)

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    if OUT_DTYPE == 0:
        tl.store(c_ptrs, acc.to(tl.float16), mask=mask_c)
    elif OUT_DTYPE == 1:
        tl.store(c_ptrs, acc.to(tl.bfloat16), mask=mask_c)
    else:
        tl.store(c_ptrs, acc.to(tl.float32), mask=mask_c)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("a and b must be CUDA tensors")
    if a.device != b.device:
        raise ValueError("a and b must be on the same device")
    if a.dtype != b.dtype:
        raise ValueError("a and b must have the same dtype")

    M, K = a.shape
    _, N = b.shape

    if a.dtype == torch.float16:
        out_dtype = 0
    elif a.dtype == torch.bfloat16:
        out_dtype = 1
    elif a.dtype == torch.float32:
        out_dtype = 2
    else:
        raise TypeError(f"unsupported dtype: {a.dtype}")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        K=K,
        stride_am=a.stride(0),
        stride_ak=a.stride(1),
        stride_bk=b.stride(0),
        stride_bn=b.stride(1),
        stride_cm=c.stride(0),
        stride_cn=c.stride(1),
        OUT_DTYPE=out_dtype,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            return {"program_path": path}
        except Exception:
            try:
                src = inspect.getsource(sys.modules[__name__])
                return {"code": src}
            except Exception:
                return {"code": ""}