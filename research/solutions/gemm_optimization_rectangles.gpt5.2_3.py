import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    x = x.to(tl.float32)
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_configs = [
    triton.Config({"BM": 128, "BN": 64, "BK": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BM": 64, "BN": 128, "BK": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BM": 128, "BN": 128, "BK": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BM": 64, "BN": 64, "BK": 64, "GROUP_M": 8}, num_warps=4, num_stages=5),
    triton.Config({"BM": 256, "BN": 64, "BK": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
    triton.Config({"BM": 64, "BN": 256, "BK": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
]


@triton.autotune(configs=_configs, key=["M", "N", "K"])
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
    BM: tl.constexpr,
    BN: tl.constexpr,
    BK: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BM)
    grid_n = tl.cdiv(N, BN)

    num_pid_in_group = GROUP_M * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group // grid_n)
    pid_n = pid_in_group - (pid_in_group // grid_n) * grid_n

    a_blk = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(pid_m * BM, 0),
        block_shape=(BM, BK),
        order=(1, 0),
    )
    b_blk = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, pid_n * BN),
        block_shape=(BK, BN),
        order=(0, 1),
    )

    acc = tl.zeros((BM, BN), dtype=tl.float32)

    k = 0
    while k < K:
        a = tl.load(a_blk, boundary_check=(0,), padding_option="zero")
        b = tl.load(b_blk, boundary_check=(1,), padding_option="zero")
        acc += tl.dot(a, b, out_dtype=tl.float32)
        a_blk = tl.advance(a_blk, (0, BK))
        b_blk = tl.advance(b_blk, (BK, 0))
        k += BK

    acc = gelu(acc)
    out = acc.to(OUT_DTYPE)

    c_blk = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(pid_m * BM, pid_n * BN),
        block_shape=(BM, BN),
        order=(1, 0),
    )
    tl.store(c_blk, out, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.device.type != "cuda" or b.device.type != "cuda":
        raise ValueError("a and b must be CUDA tensors")
    if a.dtype != b.dtype:
        raise ValueError("a and b must have the same dtype")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")

    M, K = a.shape
    _, N = b.shape

    out_dtype_torch = a.dtype
    if out_dtype_torch == torch.float16:
        out_dtype_tl = tl.float16
    elif out_dtype_torch == torch.bfloat16:
        out_dtype_tl = tl.bfloat16
    elif out_dtype_torch == torch.float32:
        out_dtype_tl = tl.float32
    else:
        a_ = a.float()
        b_ = b.float()
        c_ = torch.matmul(a_, b_)
        return torch.nn.functional.gelu(c_).to(a.dtype)

    c = torch.empty((M, N), device=a.device, dtype=out_dtype_torch)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    def grid(meta):
        return (triton.cdiv(M, meta["BM"]) * triton.cdiv(N, meta["BN"]),)

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
        OUT_DTYPE=out_dtype_tl,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}