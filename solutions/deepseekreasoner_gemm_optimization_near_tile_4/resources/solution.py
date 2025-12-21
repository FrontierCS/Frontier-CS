import torch
import triton
import triton.language as tl
import os
from typing import Optional

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        # Small blocks for small matrices
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=2, num_warps=4),
        
        # Medium blocks for typical workloads
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        
        # Large blocks for larger matrices
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=16),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=16),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 8}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128, 'GROUP_M': 8}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K', 'a_stride_am', 'a_stride_ak', 'b_stride_bk', 'b_stride_bn'],
)
@triton.jit
def _matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    a_stride_am, a_stride_ak,
    b_stride_bk, b_stride_bn,
    c_stride_cm, c_stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    USE_FP32_ACC: tl.constexpr = True,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    # Reorder program IDs for better L2 cache hit rate
    num_pid_m = grid_m
    num_pid_n = grid_n
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + ((pid % num_pid_in_group) % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # Offsets for A and B blocks
    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    # Pointers to A and B
    a_ptrs = a_ptr + (offs_am[:, None] * a_stride_am + offs_k[None, :] * a_stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * b_stride_bk + offs_bn[None, :] * b_stride_bn)
    
    # Initialize accumulator
    if USE_FP32_ACC:
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    else:
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float16)
    
    # Loop over K dimension
    for k in range(0, K, BLOCK_K):
        # Mask for boundaries
        mask_a = (offs_am[:, None] < M) & (offs_k[None, :] < K - k)
        mask_b = (offs_k[:, None] < K - k) & (offs_bn[None, :] < N)
        
        # Load A and B tiles
        a = tl.load(a_ptrs, mask=mask_a, other=0.0)
        b = tl.load(b_ptrs, mask=mask_b, other=0.0)
        
        # Compute matrix multiplication
        if USE_FP32_ACC:
            a = a.to(tl.float32)
            b = b.to(tl.float32)
        
        acc += tl.dot(a, b)
        
        # Move pointers to next K block
        a_ptrs += BLOCK_K * a_stride_ak
        b_ptrs += BLOCK_K * b_stride_bk
    
    # Apply GELU activation
    acc = gelu(acc)
    
    # Convert back to original dtype for output
    if USE_FP32_ACC:
        acc = acc.to(c_ptr.dtype.element_ty)
    
    # Write back C
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_ptrs = c_ptr + (offs_cm[:, None] * c_stride_cm + offs_cn[None, :] * c_stride_cn)
    mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, acc, mask=mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Check inputs
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D tensors"
    assert a.shape[1] == b.shape[0], f"Shapes {a.shape} and {b.shape} cannot be multiplied"
    
    M, K = a.shape
    K_check, N = b.shape
    assert K == K_check, f"Dimension mismatch: {K} != {K_check}"
    
    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Handle small matrices with torch.matmul + GELU
    if M * N * K < 1024:
        return torch.nn.functional.gelu(torch.matmul(a, b))
    
    # Launch kernel
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        USE_FP32_ACC=a.dtype in [torch.float16, torch.bfloat16]
    )
    
    return c

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> dict:
        # Get the source code of the current module
        import inspect
        import sys
        
        # Get the module containing matmul function
        current_module = sys.modules[__name__]
        source = inspect.getsource(current_module)
        
        return {"code": source}
