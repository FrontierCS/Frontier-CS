import torch
import triton
import triton.language as tl
import os
from typing import Optional, Dict, Any

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def _matmul_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    USE_ACCUMULATOR_SPLIT: tl.constexpr,
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    width = GROUP_M * grid_n
    group_id = pid // width
    group_size = min(grid_m - group_id * GROUP_M, GROUP_M)
    pid_m = group_id * GROUP_M + (pid % group_size)
    pid_n = (pid % width) // group_size
    
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    ram = tl.max_contiguous(tl.multiple_of(rm % M, BLOCK_M), BLOCK_M)
    rbn = tl.max_contiguous(tl.multiple_of(rn % N, BLOCK_N), BLOCK_N)
    
    rk = tl.arange(0, BLOCK_K)
    A_ptr = A + (ram[:, None] * stride_am + rk[None, :] * stride_ak)
    B_ptr = B + (rk[:, None] * stride_bk + rbn[None, :] * stride_bn)
    
    acc0 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32) if USE_ACCUMULATOR_SPLIT else None
    
    if USE_ACCUMULATOR_SPLIT:
        for k in range(0, K, BLOCK_K * 2):
            a0 = tl.load(A_ptr, mask=rk[None, :] < K - k, other=0.0)
            b0 = tl.load(B_ptr, mask=rk[:, None] < K - k, other=0.0)
            acc0 += tl.dot(a0, b0, allow_tf32=True)
            
            a1 = tl.load(A_ptr + BLOCK_K * stride_ak, 
                        mask=rk[None, :] < K - k - BLOCK_K, other=0.0)
            b1 = tl.load(B_ptr + BLOCK_K * stride_bk, 
                        mask=rk[:, None] < K - k - BLOCK_K, other=0.0)
            acc1 += tl.dot(a1, b1, allow_tf32=True)
            
            A_ptr += BLOCK_K * 2 * stride_ak
            B_ptr += BLOCK_K * 2 * stride_bk
        acc = acc0 + acc1
    else:
        for k in range(0, K, BLOCK_K):
            a = tl.load(A_ptr, mask=rk[None, :] < K - k, other=0.0)
            b = tl.load(B_ptr, mask=rk[:, None] < K - k, other=0.0)
            acc0 += tl.dot(a, b, allow_tf32=True)
            A_ptr += BLOCK_K * stride_ak
            B_ptr += BLOCK_K * stride_bk
        acc = acc0
    
    acc = gelu(acc.to(tl.float32))
    
    C_ptr = C + (ram[:, None] * stride_cm + rbn[None, :] * stride_cn)
    mask = (rm < M)[:, None] & (rn < N)[None, :]
    tl.store(C_ptr, acc, mask=mask)

def _get_config(M, N, K):
    device = torch.cuda.current_device()
    cc = torch.cuda.get_device_capability(device)
    
    if cc[0] >= 8:
        if M >= 1024 and N <= 256:
            configs = [
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
                {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            ]
        elif N >= 1024 and M <= 256:
            configs = [
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
                {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            ]
        else:
            configs = [
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
                {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            ]
    else:
        configs = [
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
        ]
    
    return configs[0]

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D tensors"
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    
    M, K = a.shape
    K, N = b.shape
    
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    config = _get_config(M, N, K)
    EVEN_K = K % (config['BLOCK_K'] * (2 if config['USE_ACCUMULATOR_SPLIT'] else 1)) == 0
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        EVEN_K=EVEN_K,
        **config
    )
    
    return c

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, Any]:
        code = '''import torch
import triton
import triton.language as tl
import os
from typing import Optional, Dict, Any

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def _matmul_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    USE_ACCUMULATOR_SPLIT: tl.constexpr,
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    width = GROUP_M * grid_n
    group_id = pid // width
    group_size = min(grid_m - group_id * GROUP_M, GROUP_M)
    pid_m = group_id * GROUP_M + (pid % group_size)
    pid_n = (pid % width) // group_size
    
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    ram = tl.max_contiguous(tl.multiple_of(rm % M, BLOCK_M), BLOCK_M)
    rbn = tl.max_contiguous(tl.multiple_of(rn % N, BLOCK_N), BLOCK_N)
    
    rk = tl.arange(0, BLOCK_K)
    A_ptr = A + (ram[:, None] * stride_am + rk[None, :] * stride_ak)
    B_ptr = B + (rk[:, None] * stride_bk + rbn[None, :] * stride_bn)
    
    acc0 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32) if USE_ACCUMULATOR_SPLIT else None
    
    if USE_ACCUMULATOR_SPLIT:
        for k in range(0, K, BLOCK_K * 2):
            a0 = tl.load(A_ptr, mask=rk[None, :] < K - k, other=0.0)
            b0 = tl.load(B_ptr, mask=rk[:, None] < K - k, other=0.0)
            acc0 += tl.dot(a0, b0, allow_tf32=True)
            
            a1 = tl.load(A_ptr + BLOCK_K * stride_ak, 
                        mask=rk[None, :] < K - k - BLOCK_K, other=0.0)
            b1 = tl.load(B_ptr + BLOCK_K * stride_bk, 
                        mask=rk[:, None] < K - k - BLOCK_K, other=0.0)
            acc1 += tl.dot(a1, b1, allow_tf32=True)
            
            A_ptr += BLOCK_K * 2 * stride_ak
            B_ptr += BLOCK_K * 2 * stride_bk
        acc = acc0 + acc1
    else:
        for k in range(0, K, BLOCK_K):
            a = tl.load(A_ptr, mask=rk[None, :] < K - k, other=0.0)
            b = tl.load(B_ptr, mask=rk[:, None] < K - k, other=0.0)
            acc0 += tl.dot(a, b, allow_tf32=True)
            A_ptr += BLOCK_K * stride_ak
            B_ptr += BLOCK_K * stride_bk
        acc = acc0
    
    acc = gelu(acc.to(tl.float32))
    
    C_ptr = C + (ram[:, None] * stride_cm + rbn[None, :] * stride_cn)
    mask = (rm < M)[:, None] & (rn < N)[None, :]
    tl.store(C_ptr, acc, mask=mask)

def _get_config(M, N, K):
    device = torch.cuda.current_device()
    cc = torch.cuda.get_device_capability(device)
    
    if cc[0] >= 8:
        if M >= 1024 and N <= 256:
            configs = [
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
                {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            ]
        elif N >= 1024 and M <= 256:
            configs = [
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
                {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            ]
        else:
            configs = [
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
                {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': True},
                {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            ]
    else:
        configs = [
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'USE_ACCUMULATOR_SPLIT': False},
        ]
    
    return configs[0]

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D tensors"
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    
    M, K = a.shape
    K, N = b.shape
    
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    config = _get_config(M, N, K)
    EVEN_K = K % (config['BLOCK_K'] * (2 if config['USE_ACCUMULATOR_SPLIT'] else 1)) == 0
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        EVEN_K=EVEN_K,
        **config
    )
    
    return c
'''
        return {"code": code}
