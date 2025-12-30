import os
import sys
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_AUTOTUNE_CONFIGS = [
    triton.Config({"BM": 256, "BN": 64, "BK": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BM": 256, "BN": 64, "BK": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BM": 128, "BN": 64, "BK": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BM": 128, "BN": 64, "BK": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BM": 128, "BN": 128, "BK": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BM": 128, "BN": 128, "BK": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BM": 64, "BN": 128, "BK": 64, "GROUP_M": 4}, num_warps=4, num_stages=4),
    triton.Config({"BM": 64, "BN": 128, "BK": 32, "GROUP_M": 4}, num_warps=4, num_stages=4),
    triton.Config({"BM": 64, "BN": 256, "BK": 64, "GROUP_M": 4}, num_warps=8, num_stages=3),
    triton.Config({"BM": 64, "BN": 256, "BK": 32, "GROUP_M": 4}, num_warps=8, num_stages=3),
]


@triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["M", "N", "K"])
@triton.jit
def _matmul_gelu_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    K: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BK: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BM)
    grid_n = tl.cdiv(N, BN)

    group_size_m = GROUP_M
    num_pid_in_group = group_size_m * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size_m
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    a_block_ptr = tl.make_block_ptr(
        base=A_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(pid_m * BM, 0),
        block_shape=(BM, BK),
        order=(1, 0),
    )
    b_block_ptr = tl.make_block_ptr(
        base=B_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, pid_n * BN),
        block_shape=(BK, BN),
        order=(0, 1),
    )

    acc = tl.zeros((BM, BN), dtype=tl.float32)

    tl.multiple_of(BK, 16)
    tl.multiple_of(BM, 16)
    tl.multiple_of(BN, 16)

    for _ in range(0, K, BK):
        a = tl.load(a_block_ptr, boundary_check=(0,), padding_option="zero")
        b = tl.load(b_block_ptr, boundary_check=(1,), padding_option="zero")
        acc += tl.dot(a, b)
        a_block_ptr = tl.advance(a_block_ptr, (0, BK))
        b_block_ptr = tl.advance(b_block_ptr, (BK, 0))

    acc = gelu(acc)

    c_block_ptr = tl.make_block_ptr(
        base=C_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(pid_m * BM, pid_n * BN),
        block_shape=(BM, BN),
        order=(1, 0),
    )
    tl.store(c_block_ptr, acc, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("a and b must be CUDA tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")
    if a.dtype != b.dtype:
        raise ValueError("a and b must have the same dtype")

    M, K = a.shape
    _, N = b.shape

    if a.dtype not in (torch.float16, torch.bfloat16):
        c = a @ b
        return torch.nn.functional.gelu(c, approximate="none")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride(0), a.stride(1)
    stride_bk, stride_bn = b.stride(0), b.stride(1)
    stride_cm, stride_cn = c.stride(0), c.stride(1)

    grid = lambda META: (triton.cdiv(M, META["BM"]) * triton.cdiv(N, META["BN"]),)
    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        stride_am=stride_am,
        stride_ak=stride_ak,
        stride_bk=stride_bk,
        stride_bn=stride_bn,
        stride_cm=stride_cm,
        stride_cn=stride_cn,
        K=K,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": os.path.abspath(__file__)}
        except Exception:
            import inspect

            return {"code": inspect.getsource(sys.modules[__name__])}