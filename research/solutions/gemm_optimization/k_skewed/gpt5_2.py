import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config(dict(BLOCK_M=128, BLOCK_N=128, BLOCK_K=32, GROUP_M=8), num_warps=8, num_stages=4),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=256, BLOCK_K=32, GROUP_M=8), num_warps=8, num_stages=4),
        triton.Config(dict(BLOCK_M=256, BLOCK_N=64,  BLOCK_K=32, GROUP_M=8), num_warps=8, num_stages=4),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=64,  BLOCK_K=32, GROUP_M=8), num_warps=4, num_stages=4),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=128, BLOCK_K=32, GROUP_M=8), num_warps=4, num_stages=4),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=64,  BLOCK_K=32, GROUP_M=8), num_warps=4, num_stages=3),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=128, BLOCK_K=64, GROUP_M=4), num_warps=8, num_stages=5),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=256, BLOCK_K=64, GROUP_M=4), num_warps=8, num_stages=5),
        triton.Config(dict(BLOCK_M=256, BLOCK_N=128, BLOCK_K=64, GROUP_M=4), num_warps=8, num_stages=5),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=128, BLOCK_K=64, GROUP_M=4), num_warps=4, num_stages=5),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=64,  BLOCK_K=64, GROUP_M=4), num_warps=4, num_stages=5),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    group_id = pid // (group_size * num_pid_n)
    first_pid_m = group_id * group_size
    pid_in_group = pid % (group_size * num_pid_n)
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_remaining = K
    while k_remaining > 0:
        k_mask_row = offs_k[None, :] < k_remaining
        k_mask_col = k_mask_row.T
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_row, other=0.0)
        b = tl.load(b_ptrs, mask=k_mask_col & (offs_n[None, :] < N), other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_remaining -= BLOCK_K

    acc = gelu(acc)

    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible matrix shapes")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")

    dtype = torch.promote_types(a.dtype, b.dtype)
    supported = (torch.float16, torch.bfloat16, torch.float32)
    if dtype not in supported:
        dtype = torch.float32
    if a.dtype != dtype:
        a = a.to(dtype)
    if b.dtype != dtype:
        b = b.to(dtype)

    M, K = a.shape
    _, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=dtype)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

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
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config(dict(BLOCK_M=128, BLOCK_N=128, BLOCK_K=32, GROUP_M=8), num_warps=8, num_stages=4),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=256, BLOCK_K=32, GROUP_M=8), num_warps=8, num_stages=4),
        triton.Config(dict(BLOCK_M=256, BLOCK_N=64,  BLOCK_K=32, GROUP_M=8), num_warps=8, num_stages=4),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=64,  BLOCK_K=32, GROUP_M=8), num_warps=4, num_stages=4),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=128, BLOCK_K=32, GROUP_M=8), num_warps=4, num_stages=4),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=64,  BLOCK_K=32, GROUP_M=8), num_warps=4, num_stages=3),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=128, BLOCK_K=64, GROUP_M=4), num_warps=8, num_stages=5),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=256, BLOCK_K=64, GROUP_M=4), num_warps=8, num_stages=5),
        triton.Config(dict(BLOCK_M=256, BLOCK_N=128, BLOCK_K=64, GROUP_M=4), num_warps=8, num_stages=5),
        triton.Config(dict(BLOCK_M=64,  BLOCK_N=128, BLOCK_K=64, GROUP_M=4), num_warps=4, num_stages=5),
        triton.Config(dict(BLOCK_M=128, BLOCK_N=64,  BLOCK_K=64, GROUP_M=4), num_warps=4, num_stages=5),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    group_id = pid // (group_size * num_pid_n)
    first_pid_m = group_id * group_size
    pid_in_group = pid % (group_size * num_pid_n)
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_remaining = K
    while k_remaining > 0:
        k_mask_row = offs_k[None, :] < k_remaining
        k_mask_col = k_mask_row.T
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_row, other=0.0)
        b = tl.load(b_ptrs, mask=k_mask_col & (offs_n[None, :] < N), other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_remaining -= BLOCK_K

    acc = gelu(acc)

    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible matrix shapes")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")

    dtype = torch.promote_types(a.dtype, b.dtype)
    supported = (torch.float16, torch.bfloat16, torch.float32)
    if dtype not in supported:
        dtype = torch.float32
    if a.dtype != dtype:
        a = a.to(dtype)
    if b.dtype != dtype:
        b = b.to(dtype)

    M, K = a.shape
    _, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=dtype)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )

    return c
'''
        return {"code": code}