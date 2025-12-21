import torch
import triton
import triton.language as tl
import os


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.jit
def _matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
    SPLIT_K: tl.constexpr = 1,
):
    pid = tl.program_id(0)
    pid_z = tl.program_id(1)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    grid_mn = grid_m * grid_n
    
    num_pid_mn = grid_mn // SPLIT_K
    if SPLIT_K > 1:
        pid_mn = pid % num_pid_mn
        pid_k = pid // num_pid_mn
    else:
        pid_mn = pid
        pid_k = 0
    
    if GROUP_M == 1:
        pid_m = pid_mn // grid_n
        pid_n = pid_mn % grid_n
    else:
        width = GROUP_M * grid_n
        group_id = pid_mn // width
        group_size = min(grid_m - group_id * GROUP_M, GROUP_M)
        pid_m = group_id * GROUP_M + (pid_mn % group_size)
        pid_n = (pid_mn // group_size) % grid_n
    
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    ram = tl.max_contiguous(tl.multiple_of(rm % M, BLOCK_M), BLOCK_M)
    rbn = tl.max_contiguous(tl.multiple_of(rn % N, BLOCK_N), BLOCK_N)
    rk = tl.arange(0, BLOCK_K)
    
    if SPLIT_K > 1:
        k_start = pid_k * (K // SPLIT_K)
        k_end = (pid_k + 1) * (K // SPLIT_K) if pid_k < SPLIT_K - 1 else K
    else:
        k_start = 0
        k_end = K
    
    a_ptrs = a_ptr + ram[:, None] * stride_am + rk[None, :] * stride_ak
    b_ptrs = b_ptr + rk[:, None] * stride_bk + rbn[None, :] * stride_bn
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    if EVEN_K:
        for k in range(k_start, k_end, BLOCK_K):
            a = tl.load(a_ptrs, mask=rk[None, :] < k_end - k, other=0.0)
            b = tl.load(b_ptrs, mask=rk[:, None] < k_end - k, other=0.0)
            accumulator += tl.dot(a, b, allow_tf32=True)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    else:
        for k in range(k_start, k_end, BLOCK_K):
            k_remaining = k_end - k
            a = tl.load(a_ptrs, mask=rk[None, :] < k_remaining, other=0.0)
            b = tl.load(b_ptrs, mask=rk[:, None] < k_remaining, other=0.0)
            accumulator += tl.dot(a, b, allow_tf32=True)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    
    accumulator = gelu(accumulator)
    
    if SPLIT_K > 1:
        accumulator = accumulator.to(tl.float32)
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        
        if pid_k == 0:
            tl.store(c_ptrs, accumulator, mask=c_mask)
        else:
            tl.atomic_add(c_ptrs, accumulator, mask=c_mask)
    else:
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        tl.store(c_ptrs, accumulator, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    M, K = a.shape
    _, N = b.shape
    
    a = a.contiguous()
    b = b.contiguous()
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    def get_config(M, N, K):
        if max(M, N, K) <= 2048:
            return (64, 64, 32, 8, True, 1)
        elif max(M, N, K) <= 4096:
            return (128, 128, 32, 8, True, 1)
        else:
            return (256, 128, 32, 8, True, 1)
    
    BLOCK_M, BLOCK_N, BLOCK_K, GROUP_M, EVEN_K, SPLIT_K = get_config(M, N, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']) * META['SPLIT_K'],
        META['SPLIT_K']
    )
    
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        EVEN_K=EVEN_K,
        SPLIT_K=SPLIT_K,
        num_warps=8 if BLOCK_M <= 128 else 16,
        num_stages=4,
    )
    
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.jit
def _matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
    SPLIT_K: tl.constexpr = 1,
):
    pid = tl.program_id(0)
    pid_z = tl.program_id(1)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    grid_mn = grid_m * grid_n
    
    num_pid_mn = grid_mn // SPLIT_K
    if SPLIT_K > 1:
        pid_mn = pid % num_pid_mn
        pid_k = pid // num_pid_mn
    else:
        pid_mn = pid
        pid_k = 0
    
    if GROUP_M == 1:
        pid_m = pid_mn // grid_n
        pid_n = pid_mn % grid_n
    else:
        width = GROUP_M * grid_n
        group_id = pid_mn // width
        group_size = min(grid_m - group_id * GROUP_M, GROUP_M)
        pid_m = group_id * GROUP_M + (pid_mn % group_size)
        pid_n = (pid_mn // group_size) % grid_n
    
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    ram = tl.max_contiguous(tl.multiple_of(rm % M, BLOCK_M), BLOCK_M)
    rbn = tl.max_contiguous(tl.multiple_of(rn % N, BLOCK_N), BLOCK_N)
    rk = tl.arange(0, BLOCK_K)
    
    if SPLIT_K > 1:
        k_start = pid_k * (K // SPLIT_K)
        k_end = (pid_k + 1) * (K // SPLIT_K) if pid_k < SPLIT_K - 1 else K
    else:
        k_start = 0
        k_end = K
    
    a_ptrs = a_ptr + ram[:, None] * stride_am + rk[None, :] * stride_ak
    b_ptrs = b_ptr + rk[:, None] * stride_bk + rbn[None, :] * stride_bn
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    if EVEN_K:
        for k in range(k_start, k_end, BLOCK_K):
            a = tl.load(a_ptrs, mask=rk[None, :] < k_end - k, other=0.0)
            b = tl.load(b_ptrs, mask=rk[:, None] < k_end - k, other=0.0)
            accumulator += tl.dot(a, b, allow_tf32=True)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    else:
        for k in range(k_start, k_end, BLOCK_K):
            k_remaining = k_end - k
            a = tl.load(a_ptrs, mask=rk[None, :] < k_remaining, other=0.0)
            b = tl.load(b_ptrs, mask=rk[:, None] < k_remaining, other=0.0)
            accumulator += tl.dot(a, b, allow_tf32=True)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    
    accumulator = gelu(accumulator)
    
    if SPLIT_K > 1:
        accumulator = accumulator.to(tl.float32)
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        
        if pid_k == 0:
            tl.store(c_ptrs, accumulator, mask=c_mask)
        else:
            tl.atomic_add(c_ptrs, accumulator, mask=c_mask)
    else:
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        tl.store(c_ptrs, accumulator, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    M, K = a.shape
    _, N = b.shape
    
    a = a.contiguous()
    b = b.contiguous()
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    def get_config(M, N, K):
        if max(M, N, K) <= 2048:
            return (64, 64, 32, 8, True, 1)
        elif max(M, N, K) <= 4096:
            return (128, 128, 32, 8, True, 1)
        else:
            return (256, 128, 32, 8, True, 1)
    
    BLOCK_M, BLOCK_N, BLOCK_K, GROUP_M, EVEN_K, SPLIT_K = get_config(M, N, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']) * META['SPLIT_K'],
        META['SPLIT_K']
    )
    
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        EVEN_K=EVEN_K,
        SPLIT_K=SPLIT_K,
        num_warps=8 if BLOCK_M <= 128 else 16,
        num_stages=4,
    )
    
    return c
'''
        return {"code": code}
