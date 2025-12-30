import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _matmul_configs():
    cfgs = []
    for bm, bn, bk, warps, stages, gm in [
        (128, 128, 32, 8, 5, 8),
        (128, 256, 32, 8, 5, 8),
        (256, 128, 32, 8, 5, 8),
        (64, 256, 32, 8, 5, 8),
        (256, 64, 32, 8, 5, 8),
        (128, 64, 32, 4, 5, 8),
        (64, 128, 32, 4, 5, 8),
        (64, 64, 32, 4, 4, 8),
        (128, 128, 64, 8, 4, 8),
        (64, 128, 64, 4, 4, 8),
        (128, 256, 64, 8, 4, 8),
        (256, 128, 64, 8, 4, 8),
        (128, 128, 32, 8, 5, 4),
        (128, 256, 32, 8, 5, 4),
        (256, 128, 32, 8, 5, 4),
    ]:
        cfgs.append(
            triton.Config(
                {
                    "BLOCK_M": bm,
                    "BLOCK_N": bn,
                    "BLOCK_K": bk,
                    "GROUP_M": gm,
                },
                num_warps=warps,
                num_stages=stages,
            )
        )
    return cfgs


@triton.autotune(
    configs=_matmul_configs(),
    key=["M", "N", "K"],
)
@triton.heuristics(
    {
        "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
    }
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
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
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(grid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    a_bp = tl.make_block_ptr(
        base=A_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_bp = tl.make_block_ptr(
        base=B_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, pid_n * BLOCK_N),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        for _ in range(0, K, BLOCK_K):
            a = tl.load(a_bp, boundary_check=(0,), padding_option="zero")
            b = tl.load(b_bp, boundary_check=(1,), padding_option="zero", cache_modifier=".ca")
            acc += tl.dot(a, b)
            a_bp = tl.advance(a_bp, (0, BLOCK_K))
            b_bp = tl.advance(b_bp, (BLOCK_K, 0))
    else:
        for _ in range(0, K, BLOCK_K):
            a = tl.load(a_bp, boundary_check=(0, 1), padding_option="zero")
            b = tl.load(b_bp, boundary_check=(0, 1), padding_option="zero", cache_modifier=".ca")
            acc += tl.dot(a, b)
            a_bp = tl.advance(a_bp, (0, BLOCK_K))
            b_bp = tl.advance(b_bp, (BLOCK_K, 0))

    acc = gelu(acc)
    out = acc.to(OUT_DTYPE)

    c_bp = tl.make_block_ptr(
        base=C_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    tl.store(c_bp, out, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not isinstance(a, torch.Tensor) or not isinstance(b, torch.Tensor):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        return torch.nn.functional.gelu(a @ b)
    if not a.is_cuda or not b.is_cuda:
        return torch.nn.functional.gelu(a @ b)

    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")

    if a.dtype != b.dtype:
        return torch.nn.functional.gelu(a @ b)

    if a.dtype == torch.float16:
        out_dtype = torch.float16
        out_tl = tl.float16
    elif a.dtype == torch.bfloat16:
        out_dtype = torch.bfloat16
        out_tl = tl.bfloat16
    elif a.dtype == torch.float32:
        return torch.nn.functional.gelu(a @ b)
    else:
        return torch.nn.functional.gelu(a @ b)

    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        K=K,
        stride_am=stride_am,
        stride_ak=stride_ak,
        stride_bk=stride_bk,
        stride_bn=stride_bn,
        stride_cm=stride_cm,
        stride_cn=stride_cn,
        OUT_DTYPE=out_tl,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}