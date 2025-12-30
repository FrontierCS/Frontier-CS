import textwrap

KERNEL_CODE = textwrap.dedent(
    r"""
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=5),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=5),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=5),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    ],
    key=["M", "N", "K"],
)
@triton.heuristics(
    {
        "EVEN_M": lambda args: (args["M"] % args["BLOCK_M"]) == 0,
        "EVEN_N": lambda args: (args["N"] % args["BLOCK_N"]) == 0,
        "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
    }
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
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group // num_pid_n)
    pid_n = pid_in_group % num_pid_n

    offs_m = pid_m * BLOCK_M
    offs_n = pid_n * BLOCK_N

    a_block_ptr = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(offs_m, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_block_ptr = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, offs_n),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(1, 0),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_M and EVEN_N and EVEN_K:
        tl.multiple_of(stride_ak, 1)
        tl.multiple_of(stride_bn, 1)
        tl.multiple_of(K, BLOCK_K)
        for _ in range(0, K, BLOCK_K):
            a = tl.load(a_block_ptr)
            b = tl.load(b_block_ptr)
            acc = tl.dot(a, b, acc)
            a_block_ptr = tl.advance(a_block_ptr, (0, BLOCK_K))
            b_block_ptr = tl.advance(b_block_ptr, (BLOCK_K, 0))
    else:
        for _ in range(0, K, BLOCK_K):
            a = tl.load(a_block_ptr, boundary_check=(0, 1), padding_option="zero")
            b = tl.load(b_block_ptr, boundary_check=(0, 1), padding_option="zero")
            acc = tl.dot(a, b, acc)
            a_block_ptr = tl.advance(a_block_ptr, (0, BLOCK_K))
            b_block_ptr = tl.advance(b_block_ptr, (BLOCK_K, 0))

    acc = gelu(acc)
    out = acc.to(OUT_DTYPE)

    c_block_ptr = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    if EVEN_M and EVEN_N:
        tl.store(c_block_ptr, out)
    else:
        tl.store(c_block_ptr, out, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul: expected 2D tensors")
    if a.device.type != "cuda" or b.device.type != "cuda":
        x = a @ b
        return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"matmul: incompatible shapes {tuple(a.shape)} x {tuple(b.shape)}")

    M, K = a.shape
    _, N = b.shape

    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    if a.dtype == torch.float16:
        out_dtype = tl.float16
    elif a.dtype == torch.bfloat16:
        out_dtype = tl.bfloat16
    else:
        a = a.to(torch.float16)
        b = b.to(torch.float16)
        out_dtype = tl.float16

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
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}