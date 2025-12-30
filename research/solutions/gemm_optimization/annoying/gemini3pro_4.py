import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

def get_configs():
    configs = []
    # Optimization for L4 (Ada Lovelace)
    # Larger blocks for high throughput, smaller blocks for boundary handling
    configs.append(triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8))
    configs.append(triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    configs.append(triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    configs.append(triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4))
    configs.append(triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2))
    return configs

@triton.jit
def gelu(x):
    # Implements GELU activation: 0.5 * x * (1 + erf(x / sqrt(2)))
    # Using tl.erf as it corresponds to the required math function
    return x * 0.5 * (1.0 + tl.erf(x * 0.7071067811865476))

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
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # PID mapping and L2 Cache Optimizations (Grouped Ordering)
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Offsets
    offs_am = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_bn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Pointers
    # Note: We compute pointers based on strides to handle arbitrary memory layouts
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Output Masking (M, N dimensions)
    mask_m = offs_am[:, None] < M
    mask_n = offs_bn[None, :] < N
    
    # Loop over K
    for k in range(0, K, BLOCK_SIZE_K):
        # K Masking
        # Handles cases where K is not a multiple of BLOCK_SIZE_K
        k_remaining = K - k
        mask_k = offs_k < k_remaining
        
        # Load A [BLOCK_M, BLOCK_K]
        # Mask requires checks on M (rows) and K (cols)
        a = tl.load(a_ptrs, mask=mask_m & mask_k[None, :], other=0.0)
        
        # Load B [BLOCK_K, BLOCK_N]
        # Mask requires checks on K (rows) and N (cols)
        b = tl.load(b_ptrs, mask=mask_k[:, None] & mask_n, other=0.0)
        
        accumulator = tl.dot(a, b, accumulator)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Epilogue: GELU + Store
    c = gelu(accumulator)
    
    # Store C [BLOCK_M, BLOCK_N]
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    
    tl.store(c_ptrs, c, mask=mask_m & mask_n)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    K_b, N = b.shape
    assert K == K_b, "K dimensions must match"
    
    # Output initialization
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # 1D Grid Launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), )
    
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