import torch
import triton
import triton.language as tl
from typing import Optional, Dict, Any

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, SPLIT_K: tl.constexpr,
    USE_FP16_ACC: tl.constexpr,
    EVEN_K: tl.constexpr,
    NUM_WARPS: tl.constexpr,
    NUM_STAGES: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    pid_z = tl.program_id(axis=1)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    
    if GROUP_M == 1:
        pid_m = pid // num_pid_n
        pid_n = pid % num_pid_n
    else:
        num_pid_in_group = GROUP_M * num_pid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_M
        group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
        pid_m = first_pid_m + ((pid % num_pid_in_group) % group_size_m)
        pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)
    
    if SPLIT_K > 1:
        k_step = K // SPLIT_K
        k_start = pid_z * k_step
        k_end = min(k_start + k_step, K)
        K_ITER = k_end - k_start
    else:
        k_start = 0
        K_ITER = K
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    if EVEN_K:
        for k in range(0, K_ITER, BLOCK_K):
            a = tl.load(a_ptrs + k * stride_ak)
            b = tl.load(b_ptrs + k * stride_bk)
            accumulator += tl.dot(a, b, out_dtype=tl.float32)
    else:
        for k in range(0, K_ITER, BLOCK_K):
            k_remaining = K_ITER - k
            a_mask = (offs_am[:, None] < M) & (offs_k[None, :] < k_remaining)
            b_mask = (offs_k[:, None] < k_remaining) & (offs_bn[None, :] < N)
            a = tl.load(a_ptrs + k * stride_ak, mask=a_mask, other=0.0)
            b = tl.load(b_ptrs + k * stride_bk, mask=b_mask, other=0.0)
            accumulator += tl.dot(a, b, out_dtype=tl.float32)
    
    if SPLIT_K > 1:
        accumulator = accumulator.to(tl.float16 if USE_FP16_ACC else tl.float32)
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        tl.atomic_add(c_ptrs, accumulator, mask=c_mask)
    else:
        c = gelu(accumulator)
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    assert a.is_contiguous() and b.is_contiguous(), "Inputs must be contiguous"
    
    M, K = a.shape
    K, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    def get_config(M, N, K):
        if M >= 1024 and N <= 256:
            return {
                'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32,
                'GROUP_M': 8, 'SPLIT_K': 1,
                'NUM_WARPS': 4, 'NUM_STAGES': 3,
                'USE_FP16_ACC': a.dtype == torch.float16,
                'EVEN_K': K % 32 == 0
            }
        elif N >= 1024 and M <= 256:
            return {
                'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32,
                'GROUP_M': 8, 'SPLIT_K': 1,
                'NUM_WARPS': 4, 'NUM_STAGES': 3,
                'USE_FP16_ACC': a.dtype == torch.float16,
                'EVEN_K': K % 32 == 0
            }
        else:
            return {
                'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32,
                'GROUP_M': 8, 'SPLIT_K': 1,
                'NUM_WARPS': 4, 'NUM_STAGES': 3,
                'USE_FP16_ACC': a.dtype == torch.float16,
                'EVEN_K': K % 32 == 0
            }
    
    config = get_config(M, N, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        META['SPLIT_K']
    )
    
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        **config
    )
    
    return c

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
from typing import Optional, Dict, Any

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, SPLIT_K: tl.constexpr,
    USE_FP16_ACC: tl.constexpr,
    EVEN_K: tl.constexpr,
    NUM_WARPS: tl.constexpr,
    NUM_STAGES: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    pid_z = tl.program_id(axis=1)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    
    if GROUP_M == 1:
        pid_m = pid // num_pid_n
        pid_n = pid % num_pid_n
    else:
        num_pid_in_group = GROUP_M * num_pid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_M
        group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
        pid_m = first_pid_m + ((pid % num_pid_in_group) % group_size_m)
        pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)
    
    if SPLIT_K > 1:
        k_step = K // SPLIT_K
        k_start = pid_z * k_step
        k_end = min(k_start + k_step, K)
        K_ITER = k_end - k_start
    else:
        k_start = 0
        K_ITER = K
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    if EVEN_K:
        for k in range(0, K_ITER, BLOCK_K):
            a = tl.load(a_ptrs + k * stride_ak)
            b = tl.load(b_ptrs + k * stride_bk)
            accumulator += tl.dot(a, b, out_dtype=tl.float32)
    else:
        for k in range(0, K_ITER, BLOCK_K):
            k_remaining = K_ITER - k
            a_mask = (offs_am[:, None] < M) & (offs_k[None, :] < k_remaining)
            b_mask = (offs_k[:, None] < k_remaining) & (offs_bn[None, :] < N)
            a = tl.load(a_ptrs + k * stride_ak, mask=a_mask, other=0.0)
            b = tl.load(b_ptrs + k * stride_bk, mask=b_mask, other=0.0)
            accumulator += tl.dot(a, b, out_dtype=tl.float32)
    
    if SPLIT_K > 1:
        accumulator = accumulator.to(tl.float16 if USE_FP16_ACC else tl.float32)
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        tl.atomic_add(c_ptrs, accumulator, mask=c_mask)
    else:
        c = gelu(accumulator)
        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
        c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
        tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    assert a.is_contiguous() and b.is_contiguous(), "Inputs must be contiguous"
    
    M, K = a.shape
    K, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    def get_config(M, N, K):
        if M >= 1024 and N <= 256:
            return {
                'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32,
                'GROUP_M': 8, 'SPLIT_K': 1,
                'NUM_WARPS': 4, 'NUM_STAGES': 3,
                'USE_FP16_ACC': a.dtype == torch.float16,
                'EVEN_K': K % 32 == 0
            }
        elif N >= 1024 and M <= 256:
            return {
                'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32,
                'GROUP_M': 8, 'SPLIT_K': 1,
                'NUM_WARPS': 4, 'NUM_STAGES': 3,
                'USE_FP16_ACC': a.dtype == torch.float16,
                'EVEN_K': K % 32 == 0
            }
        else:
            return {
                'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32,
                'GROUP_M': 8, 'SPLIT_K': 1,
                'NUM_WARPS': 4, 'NUM_STAGES': 3,
                'USE_FP16_ACC': a.dtype == torch.float16,
                'EVEN_K': K % 32 == 0
            }
    
    config = get_config(M, N, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        META['SPLIT_K']
    )
    
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        **config
    )
    
    return c
'''
        return {"code": code}