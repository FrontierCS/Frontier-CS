import torch
import triton
import triton.language as tl
import os
import math
from typing import Dict, Any

# Required GELU implementation
@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        # Transformer-optimized configurations
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        # For tall-skinny matrices
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        # For wide-short matrices
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        # For square matrices
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        # Memory-bound optimized
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128, 'GROUP_M': 8}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 8}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_kernel(
    # Pointers to matrices
    A, B, C,
    # Matrix dimensions
    M, N, K,
    # Stride information
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Create block pointers
    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    A_ptrs = A + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    B_ptrs = B + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Initialize accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    # Loop over K dimension
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Load blocks
        a = tl.load(A_ptrs, mask=offs_k[None, :] < K - k * BLOCK_K, other=0.0)
        b = tl.load(B_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        
        # Update pointers
        A_ptrs += BLOCK_K * stride_ak
        B_ptrs += BLOCK_K * stride_bk
        
        # Compute block matrix multiplication
        acc += tl.dot(a, b)
    
    # Apply GELU activation
    acc = gelu(acc)
    
    # Write back result
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    C_ptrs = C + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(C_ptrs, acc, mask=c_mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_large_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Create block pointers
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    rk = tl.arange(0, BLOCK_K)
    
    A_ptrs = A + (rm[:, None] * stride_am + rk[None, :] * stride_ak)
    B_ptrs = B + (rk[:, None] * stride_bk + rn[None, :] * stride_bn)
    
    # Prefetch initial blocks
    a = tl.load(A_ptrs, mask=(rm[:, None] < M) & (rk[None, :] < K), other=0.0)
    b = tl.load(B_ptrs, mask=(rk[:, None] < K) & (rn[None, :] < N), other=0.0)
    
    # Initialize accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    # Loop over K with software pipelining
    for k in range(0, K, BLOCK_K):
        # Prefetch next blocks
        if k + BLOCK_K < K:
            next_A_ptrs = A_ptrs + BLOCK_K * stride_ak
            next_B_ptrs = B_ptrs + BLOCK_K * stride_bk
            next_a = tl.load(next_A_ptrs, mask=(rm[:, None] < M) & (rk[None, :] < K - k - BLOCK_K), other=0.0)
            next_b = tl.load(next_B_ptrs, mask=(rk[:, None] < K - k - BLOCK_K) & (rn[None, :] < N), other=0.0)
        
        # Compute current block
        acc += tl.dot(a, b)
        
        # Update pointers and swap buffers
        if k + BLOCK_K < K:
            A_ptrs += BLOCK_K * stride_ak
            B_ptrs += BLOCK_K * stride_bk
            a = next_a
            b = next_b
    
    # Apply GELU
    acc = gelu(acc)
    
    # Write result
    C_ptrs = C + stride_cm * rm[:, None] + stride_cn * rn[None, :]
    mask = (rm[:, None] < M) & (rn[None, :] < N)
    tl.store(C_ptrs, acc, mask=mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Check inputs
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D"
    assert a.shape[1] == b.shape[0], f"Dimension mismatch: {a.shape} @ {b.shape}"
    
    M, K = a.shape
    K_, N = b.shape
    assert K == K_, f"Dimension mismatch: {a.shape} @ {b.shape}"
    
    # Ensure tensors are contiguous and on GPU
    if not a.is_cuda:
        a = a.cuda()
    if not b.is_cuda:
        b = b.cuda()
    
    a = a.contiguous()
    b = b.contiguous()
    
    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Choose kernel based on dimensions
    max_grid = 65535
    if (M * N) / (128 * 128) < max_grid:
        # Use 1D grid kernel for better load balancing
        grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
        _matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
        )
    else:
        # Use 2D grid kernel for better scalability
        grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
        _matmul_large_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
        )
    
    return c

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        # Return the code as a string
        current_file = os.path.abspath(__file__)
        
        if spec_path is not None:
            # If spec_path is provided, write code to that path
            with open(current_file, 'r') as f:
                code = f.read()
            with open(spec_path, 'w') as f:
                f.write(code)
            return {"program_path": spec_path}
        else:
            # Otherwise return code as string
            with open(current_file, 'r') as f:
                code = f.read()
            return {"code": code}