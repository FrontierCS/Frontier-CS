import torch
import triton
import triton.language as tl
from typing import Dict, Optional
from pathlib import Path

def get_autotune_configs():
    return [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2),
    ]

@triton.autotune(
    configs=get_autotune_configs(),
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_a_batch, stride_a_m, stride_a_k,
    stride_b_batch, stride_b_k, stride_b_n,
    stride_c_batch, stride_c_m, stride_c_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    pid_batch = tl.program_id(axis=2)
    
    # -----------------------------------------------------------
    # Map program ID to spatial (M, N) block
    # -----------------------------------------------------------
    num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
    num_pid_n = (N + BLOCK_N - 1) // BLOCK_N
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # -----------------------------------------------------------
    # Pointer Arithmetic
    # -----------------------------------------------------------
    # Offsets for current block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    # Base pointers for the batch
    A_batch_ptr = A_ptr + pid_batch * stride_a_batch
    B_batch_ptr = B_ptr + pid_batch * stride_b_batch
    C_batch_ptr = C_ptr + pid_batch * stride_c_batch
    
    # Initialize pointers to the first K-block
    # A shape: [M, K] -> [BLOCK_M, BLOCK_K]
    A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_a_m) + (offs_k[None, :] * stride_a_k)
    # B shape: [K, N] -> [BLOCK_K, BLOCK_N]
    B_ptrs = B_batch_ptr + (offs_k[:, None] * stride_b_k) + (offs_n[None, :] * stride_b_n)
    
    # Accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Main Loop
    # -----------------------------------------------------------
    num_k_blocks = (K + BLOCK_K - 1) // BLOCK_K
    
    for k in range(0, num_k_blocks):
        # Current k indices for masking
        k_val = k * BLOCK_K + offs_k
        
        # Boundary masking
        a_mask = (offs_m[:, None] < M) & (k_val[None, :] < K)
        b_mask = (k_val[:, None] < K) & (offs_n[None, :] < N)
        
        # Load blocks
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        
        # Matrix multiplication
        acc += tl.dot(a, b)
        
        # Advance pointers to next K-block
        A_ptrs += BLOCK_K * stride_a_k
        B_ptrs += BLOCK_K * stride_b_k
        
    # -----------------------------------------------------------
    # Store Result
    # -----------------------------------------------------------
    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_c_m) + (offs_n[None, :] * stride_c_n)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    # Cast accumulator to float16 before storing
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication using Triton.
    A: (Batch, M, K)
    B: (Batch, K, N)
    Returns C: (Batch, M, N)
    """
    # Check constraints
    assert A.dim() == 3 and B.dim() == 3
    assert A.shape[0] == B.shape[0]
    assert A.shape[2] == B.shape[1]
    
    batch_size, M, K = A.shape
    _, _, N = B.shape
    
    # Allocate output tensor
    C = torch.empty((batch_size, M, N), device=A.device, dtype=torch.float16)
    
    # Grid calculation
    def grid(META):
        return (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), 1, batch_size)
        
    # Launch kernel
    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
    )
    
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        return {"code": Path(__file__).read_text(encoding="utf-8")}
