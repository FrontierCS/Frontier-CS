import torch
import triton
import triton.language as tl
import math


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 2}, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 64, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 64, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 2}, num_warps=4),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _matmul_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, STAGES: tl.constexpr, SPLIT_K: tl.constexpr,
):
    pid = tl.program_id(0)
    pid_z = tl.program_id(1)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    if SPLIT_K > 1:
        K_blocks = tl.cdiv(K, SPLIT_K)
        pid_batch = pid_z // K_blocks
        pid_k = pid_z % K_blocks
        k_start = pid_k * BLOCK_K
        k_end = tl.minimum((pid_k + 1) * BLOCK_K, K)
        k_length = k_end - k_start
    else:
        pid_batch = pid_z
        pid_k = 0
        k_start = 0
        k_end = K
        k_length = K

    num_pid_n = grid_n // GROUP_M
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_n = group_id * num_pid_in_group
    group_size = min(num_pid_in_group, grid_n - first_pid_n)
    
    pid_n = first_pid_n + (pid - first_pid_n) % group_size
    pid_m = (pid - first_pid_n) // group_size
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    A_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    B_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    k_tile = k_start
    for k in range(0, k_length, BLOCK_K):
        a = tl.load(A_ptrs + k_tile * stride_ak, mask=offs_m[:, None] < M, other=0.0)
        b = tl.load(B_ptrs + k_tile * stride_bk, mask=offs_n[None, :] < N, other=0.0)
        acc += tl.dot(a, b, allow_tf32=True)
        k_tile += BLOCK_K
    
    if SPLIT_K > 1:
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptr = C + pid_batch * M * N + offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn
        tl.atomic_add(c_ptr, acc, mask=(offs_cm[:, None] < M) & (offs_cn[None, :] < N))
    else:
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptr = C + offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        
        if STAGES > 1:
            acc = gelu(acc)
            tl.store(c_ptr, acc, mask=c_mask)
        else:
            tl.store(c_ptr, gelu(acc), mask=c_mask)


@triton.jit
def _matmul_splitk_reduce(
    C_split, C,
    M, N, SPLIT_K,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    pid_m = pid // grid_n
    pid_n = pid % grid_n
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(SPLIT_K):
        c_split_ptr = C_split + k * M * N + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
        acc += tl.load(c_split_ptr, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N), other=0.0)
    
    acc = gelu(acc)
    c_ptr = C + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptr, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.is_cuda and b.is_cuda, "Inputs must be on GPU"
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D"
    assert a.size(1) == b.size(0), "Matrix dimensions mismatch"
    
    M, K = a.shape
    K, N = b.shape
    
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),
        META["SPLIT_K"],
    )
    
    if a.dtype == torch.float16:
        a = a.to(torch.float32)
        b = b.to(torch.float32)
    
    if grid(_matmul_kernel.best_config)[1] > 1:
        c_split = torch.zeros((_matmul_kernel.best_config["SPLIT_K"], M, N), device=a.device, dtype=torch.float32)
        _matmul_kernel[grid](
            a, b, c_split,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c_split.stride(1), c_split.stride(2),
            GROUP_M=8,
        )
        
        grid_reduce = (triton.cdiv(M, 128) * triton.cdiv(N, 128),)
        _matmul_splitk_reduce[grid_reduce](
            c_split, c,
            M, N, _matmul_kernel.best_config["SPLIT_K"],
            c.stride(0), c.stride(1),
            BLOCK_M=128, BLOCK_N=128,
        )
    else:
        _matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
            GROUP_M=8,
        )
    
    if a.dtype == torch.float16:
        c = c.to(torch.float16)
    
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
import math


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 2}, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=8),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 64, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 1}, num_warps=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 64, "GROUP_M": 8, "STAGES": 3, "SPLIT_K": 2}, num_warps=4),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _matmul_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, STAGES: tl.constexpr, SPLIT_K: tl.constexpr,
):
    pid = tl.program_id(0)
    pid_z = tl.program_id(1)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    if SPLIT_K > 1:
        K_blocks = tl.cdiv(K, SPLIT_K)
        pid_batch = pid_z // K_blocks
        pid_k = pid_z % K_blocks
        k_start = pid_k * BLOCK_K
        k_end = tl.minimum((pid_k + 1) * BLOCK_K, K)
        k_length = k_end - k_start
    else:
        pid_batch = pid_z
        pid_k = 0
        k_start = 0
        k_end = K
        k_length = K

    num_pid_n = grid_n // GROUP_M
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_n = group_id * num_pid_in_group
    group_size = min(num_pid_in_group, grid_n - first_pid_n)
    
    pid_n = first_pid_n + (pid - first_pid_n) % group_size
    pid_m = (pid - first_pid_n) // group_size
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    A_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    B_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    k_tile = k_start
    for k in range(0, k_length, BLOCK_K):
        a = tl.load(A_ptrs + k_tile * stride_ak, mask=offs_m[:, None] < M, other=0.0)
        b = tl.load(B_ptrs + k_tile * stride_bk, mask=offs_n[None, :] < N, other=0.0)
        acc += tl.dot(a, b, allow_tf32=True)
        k_tile += BLOCK_K
    
    if SPLIT_K > 1:
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptr = C + pid_batch * M * N + offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn
        tl.atomic_add(c_ptr, acc, mask=(offs_cm[:, None] < M) & (offs_cn[None, :] < N))
    else:
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptr = C + offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        
        if STAGES > 1:
            acc = gelu(acc)
            tl.store(c_ptr, acc, mask=c_mask)
        else:
            tl.store(c_ptr, gelu(acc), mask=c_mask)


@triton.jit
def _matmul_splitk_reduce(
    C_split, C,
    M, N, SPLIT_K,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    pid_m = pid // grid_n
    pid_n = pid % grid_n
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(SPLIT_K):
        c_split_ptr = C_split + k * M * N + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
        acc += tl.load(c_split_ptr, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N), other=0.0)
    
    acc = gelu(acc)
    c_ptr = C + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptr, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.is_cuda and b.is_cuda, "Inputs must be on GPU"
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D"
    assert a.size(1) == b.size(0), "Matrix dimensions mismatch"
    
    M, K = a.shape
    K, N = b.shape
    
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),
        META["SPLIT_K"],
    )
    
    if a.dtype == torch.float16:
        a = a.to(torch.float32)
        b = b.to(torch.float32)
    
    if grid(_matmul_kernel.best_config)[1] > 1:
        c_split = torch.zeros((_matmul_kernel.best_config["SPLIT_K"], M, N), device=a.device, dtype=torch.float32)
        _matmul_kernel[grid](
            a, b, c_split,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c_split.stride(1), c_split.stride(2),
            GROUP_M=8,
        )
        
        grid_reduce = (triton.cdiv(M, 128) * triton.cdiv(N, 128),)
        _matmul_splitk_reduce[grid_reduce](
            c_split, c,
            M, N, _matmul_kernel.best_config["SPLIT_K"],
            c.stride(0), c.stride(1),
            BLOCK_M=128, BLOCK_N=128,
        )
    else:
        _matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
            GROUP_M=8,
        )
    
    if a.dtype == torch.float16:
        c = c.to(torch.float16)
    
    return c
'''
        return {"code": code}