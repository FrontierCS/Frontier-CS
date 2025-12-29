import typing

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl
import sys

# Dynamic lookup for erf implementation to ensure compatibility across Triton versions
# while satisfying the requirement to use specialized implementations if available.
def get_erf_impl():
    try:
        # Try the specifically requested libdevice path first
        from triton.language.extra.cuda import libdevice
        return libdevice.erf
    except ImportError:
        pass
    try:
        # Fallback to standard math module in newer Triton
        return tl.math.erf
    except AttributeError:
        pass
    # Final fallback
    return tl.erf

erf_impl = get_erf_impl()

@triton.jit
def gelu(x):
    """
    GELU activation function: 0.5 * x * (1 + erf(x / sqrt(2)))
    """
    return x * 0.5 * (1.0 + erf_impl(x * 0.7071067811865476))

def get_configs():
    configs = []
    # Optimization for L4 (Ada Lovelace)
    # Balanced configurations for various M, N and skewed K
    
    # High throughput configs for large matrices
    configs.append(triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8))
    configs.append(triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    configs.append(triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    
    # Configs for smaller shapes and better occupancy
    configs.append(triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    configs.append(triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    configs.append(triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    
    # Large K specific configs (larger BLOCK_K)
    configs.append(triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4))
    configs.append(triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8))
    
    # Small K specific configs
    # When K is small (e.g. 32), BLOCK_K=16 or 32 ensures efficient loops
    configs.append(triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 16, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2))
    configs.append(triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 16, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2))
    
    return configs

@triton.autotune(
    configs=get_configs(),
    key=['M', 'N', 'K'],
)
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    # Program ID
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Compute pointers
    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)
    
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Accumulate in Float32 for precision
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Inner loop
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Handle masking for K dimension (critical for K-skewed where K might be small/unaligned)
        k_remaining = K - k * BLOCK_K
        
        if k_remaining < BLOCK_K:
            a = tl.load(a_ptrs, mask=offs_k[None, :] < k_remaining, other=0.0)
            b = tl.load(b_ptrs, mask=offs_k[:, None] < k_remaining, other=0.0)
        else:
            a = tl.load(a_ptrs)
            b = tl.load(b_ptrs)
            
        accumulator += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    # Apply GELU
    accumulator = gelu(accumulator)
    
    # Store result
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    # Triton handles casting to c_ptr dtype automatically
    tl.store(c_ptrs, accumulator, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Validation
    M, K = a.shape
    K2, N = b.shape
    assert K == K2, f"Incompatible dimensions: {a.shape} and {b.shape}"
    
    # Output allocation (preserve dtype)
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Grid definition
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    
    # Kernel launch
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1)
    )
    return c
"""
        return {"code": code}