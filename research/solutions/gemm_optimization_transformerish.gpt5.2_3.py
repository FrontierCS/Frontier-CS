import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_autotune_configs():
    configs = []
    for BM, BN, BK, nw, ns, gm in [
        (128, 128, 32, 8, 5, 8),
        (128, 128, 64, 8, 5, 8),
        (128, 64, 32, 4, 5, 8),
        (64, 128, 32, 4, 5, 8),
        (64, 128, 64, 4, 5, 8),
        (64, 64, 32, 4, 4, 8),
        (128, 256, 32, 8, 5, 4),
        (64, 256, 32, 8, 4, 4),
        (256, 128, 32, 8, 5, 4),
        (256, 64, 32, 8, 4, 4),
    ]:
        configs.append(
            triton.Config(
                {
                    "BLOCK_M": BM,
                    "BLOCK_N": BN,
                    "BLOCK_K": BK,
                    "GROUP_M": gm,
                },
                num_warps=nw,
                num_stages=ns,
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

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_remaining = K
    while k_remaining > 0:
        k_mask = offs_k < k_remaining
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
        k_remaining -= BLOCK_K

    x = gelu(acc)
    if OUT_DTYPE == 0:
        out = x.to(tl.float16)
    elif OUT_DTYPE == 1:
        out = x.to(tl.bfloat16)
    else:
        out = x.to(tl.float32)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensors")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)} b={tuple(b.shape)}")
    if not a.is_cuda or not b.is_cuda:
        x = a @ b
        return torch.nn.functional.gelu(x)

    M, K = a.shape
    _, N = b.shape

    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32) or b.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        x = a @ b
        return torch.nn.functional.gelu(x)

    if a.dtype != b.dtype:
        x = (a.to(torch.float16) @ b.to(torch.float16))
        return torch.nn.functional.gelu(x)

    out_dtype = a.dtype
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    if out_dtype == torch.float16:
        out_code = 0
    elif out_dtype == torch.bfloat16:
        out_code = 1
    else:
        out_code = 2

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
        OUT_DTYPE=out_code,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
