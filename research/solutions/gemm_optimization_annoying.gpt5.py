import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_stages=4, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=4, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_stages=3, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=5, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=5, num_warps=8),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=5, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 8}, num_stages=5, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=5, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 8}, num_stages=4, num_warps=4),
    ],
    key=["M", "N", "K"],
)
@triton.heuristics(
    {
        "EVEN_K": lambda args: args["K"] % args["BLOCK_K"] == 0,
        "EVEN_M": lambda args: args["M"] % args["BLOCK_M"] == 0,
        "EVEN_N": lambda args: args["N"] % args["BLOCK_N"] == 0,
    }
)
@triton.jit
def _matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr, EVEN_M: tl.constexpr, EVEN_N: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
    num_pid_n = (N + BLOCK_N - 1) // BLOCK_N

    group_size_m = GROUP_M
    num_pid_in_group = group_size_m * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size_m
    pid_in_group = pid % num_pid_in_group
    pid_m = (first_pid_m + (pid_in_group % group_size_m)) % num_pid_m
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        k_iter = K // BLOCK_K
        for _ in range(0, k_iter):
            a = tl.load(a_ptrs)
            b = tl.load(b_ptrs)
            acc += tl.dot(a, b)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
        k_remainder = K - k_iter * BLOCK_K
        if k_remainder > 0:
            offs_kr = tl.arange(0, BLOCK_K)
            a_ptrs_r = A + offs_m[:, None] * stride_am + (k_iter * BLOCK_K + offs_kr[None, :]) * stride_ak
            b_ptrs_r = B + (k_iter * BLOCK_K + offs_kr[:, None]) * stride_bk + offs_n[None, :] * stride_bn
            k_mask = offs_kr < k_remainder
            a = tl.load(a_ptrs_r, mask=k_mask[None, :])
            b = tl.load(b_ptrs_r, mask=k_mask[:, None])
            acc += tl.dot(a, b)
    else:
        k0 = 0
        while k0 < K:
            k_remaining = K - k0
            k_mask = offs_k < k_remaining
            a = tl.load(a_ptrs, mask=(k_mask[None, :]) & ((offs_m[:, None] < M) if not EVEN_M else True), other=0.0)
            b = tl.load(b_ptrs, mask=(k_mask[:, None]) & ((offs_n[None, :] < N) if not EVEN_N else True), other=0.0)
            acc += tl.dot(a, b)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k0 += BLOCK_K

    acc = gelu(acc)

    c_ptrs = C + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    if EVEN_M and EVEN_N:
        tl.store(c_ptrs, acc)
    else:
        tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.device.type == "cuda" and b.device.type == "cuda", "Inputs must be CUDA tensors"
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D matrices"
    assert a.shape[1] == b.shape[0], "Incompatible dimensions for matmul"
    assert a.dtype in (torch.float16, torch.bfloat16, torch.float32), "Unsupported dtype for A"
    assert b.dtype in (torch.float16, torch.bfloat16, torch.float32), "Unsupported dtype for B"
    M, K = a.shape
    Kb, N = b.shape
    out_dtype = torch.promote_types(a.dtype, b.dtype)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: ((triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"])),)

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_stages=4, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=4, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_stages=3, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=5, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=5, num_warps=8),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=5, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 8}, num_stages=5, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=5, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 8}, num_stages=4, num_warps=4),
    ],
    key=["M", "N", "K"],
)
@triton.heuristics(
    {
        "EVEN_K": lambda args: args["K"] % args["BLOCK_K"] == 0,
        "EVEN_M": lambda args: args["M"] % args["BLOCK_M"] == 0,
        "EVEN_N": lambda args: args["N"] % args["BLOCK_N"] == 0,
    }
)
@triton.jit
def _matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr, EVEN_M: tl.constexpr, EVEN_N: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
    num_pid_n = (N + BLOCK_N - 1) // BLOCK_N

    group_size_m = GROUP_M
    num_pid_in_group = group_size_m * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size_m
    pid_in_group = pid % num_pid_in_group
    pid_m = (first_pid_m + (pid_in_group % group_size_m)) % num_pid_m
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        k_iter = K // BLOCK_K
        for _ in range(0, k_iter):
            a = tl.load(a_ptrs)
            b = tl.load(b_ptrs)
            acc += tl.dot(a, b)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
        k_remainder = K - k_iter * BLOCK_K
        if k_remainder > 0:
            offs_kr = tl.arange(0, BLOCK_K)
            a_ptrs_r = A + offs_m[:, None] * stride_am + (k_iter * BLOCK_K + offs_kr[None, :]) * stride_ak
            b_ptrs_r = B + (k_iter * BLOCK_K + offs_kr[:, None]) * stride_bk + offs_n[None, :] * stride_bn
            k_mask = offs_kr < k_remainder
            a = tl.load(a_ptrs_r, mask=k_mask[None, :])
            b = tl.load(b_ptrs_r, mask=k_mask[:, None])
            acc += tl.dot(a, b)
    else:
        k0 = 0
        while k0 < K:
            k_remaining = K - k0
            k_mask = offs_k < k_remaining
            a = tl.load(a_ptrs, mask=(k_mask[None, :]) & ((offs_m[:, None] < M) if not EVEN_M else True), other=0.0)
            b = tl.load(b_ptrs, mask=(k_mask[:, None]) & ((offs_n[None, :] < N) if not EVEN_N else True), other=0.0)
            acc += tl.dot(a, b)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k0 += BLOCK_K

    acc = gelu(acc)

    c_ptrs = C + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    if EVEN_M and EVEN_N:
        tl.store(c_ptrs, acc)
    else:
        tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.device.type == "cuda" and b.device.type == "cuda", "Inputs must be CUDA tensors"
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D matrices"
    assert a.shape[1] == b.shape[0], "Incompatible dimensions for matmul"
    assert a.dtype in (torch.float16, torch.bfloat16, torch.float32), "Unsupported dtype for A"
    assert b.dtype in (torch.float16, torch.bfloat16, torch.float32), "Unsupported dtype for B"
    M, K = a.shape
    Kb, N = b.shape
    out_dtype = torch.promote_types(a.dtype, b.dtype)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: ((triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"])),)

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c
"""
        return {"code": code}
