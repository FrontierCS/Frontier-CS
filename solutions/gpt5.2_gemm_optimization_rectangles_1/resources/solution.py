import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 32, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=5),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=5),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    ],
    key=["M", "N", "K"],
)
@triton.heuristics(
    values={
        "EVEN_M": lambda args: args["M"] % args["BLOCK_M"] == 0,
        "EVEN_N": lambda args: args["N"] % args["BLOCK_N"] == 0,
        "EVEN_K": lambda args: args["K"] % args["BLOCK_K"] == 0,
    }
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M,
    N,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    K: tl.constexpr,
    EVEN_M: tl.constexpr,
    EVEN_N: tl.constexpr,
    EVEN_K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    pid_group = pid // (group_size * grid_n)
    first_pid_m = pid_group * group_size
    group_m = tl.minimum(grid_m - first_pid_m, group_size)
    pid_in_group = pid % (group_size * grid_n)
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

    offs_m = pid_m * BLOCK_M
    offs_n = pid_n * BLOCK_N

    if EVEN_M:
        a_bc = () if EVEN_K else (1,)
    else:
        a_bc = (0,) if EVEN_K else (0, 1)

    if EVEN_N:
        b_bc = () if EVEN_K else (0,)
    else:
        b_bc = (1,) if EVEN_K else (0, 1)

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
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        for _ in tl.static_range(0, K, BLOCK_K):
            a = tl.load(a_block_ptr, boundary_check=a_bc, padding_option="zero")
            b = tl.load(b_block_ptr, boundary_check=b_bc, padding_option="zero")
            acc += tl.dot(a, b, out_dtype=tl.float32, allow_tf32=True)
            a_block_ptr = tl.advance(a_block_ptr, (0, BLOCK_K))
            b_block_ptr = tl.advance(b_block_ptr, (BLOCK_K, 0))
    else:
        k_remaining = K
        while k_remaining > 0:
            a = tl.load(a_block_ptr, boundary_check=a_bc, padding_option="zero")
            b = tl.load(b_block_ptr, boundary_check=b_bc, padding_option="zero")
            acc += tl.dot(a, b, out_dtype=tl.float32, allow_tf32=True)
            a_block_ptr = tl.advance(a_block_ptr, (0, BLOCK_K))
            b_block_ptr = tl.advance(b_block_ptr, (BLOCK_K, 0))
            k_remaining -= BLOCK_K

    acc = gelu(acc)

    c_bc = ()
    if not EVEN_M:
        c_bc = (0,)
    if not EVEN_N:
        c_bc = (0, 1) if c_bc == (0,) else (1,)
        if c_bc == (1,):
            c_bc = (1,)
    if not EVEN_M and not EVEN_N:
        c_bc = (0, 1)

    c_block_ptr = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    tl.store(c_block_ptr, acc, boundary_check=c_bc)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.dim() != 2 or b.dim() != 2:
        raise ValueError("matmul expects 2D tensors a(M,K) and b(K,N)")
    if a.device.type != "cuda" or b.device.type != "cuda":
        x = a.matmul(b)
        return x * 0.5 * (1.0 + torch.erf(x * (1.0 / math.sqrt(2.0))))
    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        a = a.to(torch.float16)
    if b.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        b = b.to(torch.float16)

    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError(f"Incompatible shapes: a is {a.shape}, b is {b.shape}")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)
    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        a.stride(0),
        a.stride(1),
        b.stride(0),
        b.stride(1),
        c.stride(0),
        c.stride(1),
        K=K,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
