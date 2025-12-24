import torch
import triton
import triton.language as tl
from pathlib import Path

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": Path(__file__).read_text(encoding="utf-8")}

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    stride_a_batch, stride_b_batch, stride_c_batch,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    pid_batch = tl.program_id(axis=1)
    
    # -----------------------------------------------------------
    # Map PID to spatial coordinates (M, N) with Swizzling
    # -----------------------------------------------------------
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + ((pid % num_pid_in_group) % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # -----------------------------------------------------------
    # Pointers
    # -----------------------------------------------------------
    # Base pointers for the current batch
    A_batch_ptr = A_ptr + pid_batch * stride_a_batch
    B_batch_ptr = B_ptr + pid_batch * stride_b_batch
    C_batch_ptr = C_ptr + pid_batch * stride_c_batch
    
    # Offsets for axes
    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    # -----------------------------------------------------------
    # Compute
    # -----------------------------------------------------------
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_idxs = k + offs_k
        
        # Calculate pointers for this block
        # A: (M, K) -> stride_am, stride_ak
        a_ptrs = A_batch_ptr + (offs_am[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        # B: (K, N) -> stride_bk, stride_bn
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_bn[None, :] * stride_bn)
        
        # Calculate masks
        a_mask = (offs_am[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_bn[None, :] < N) & (k_idxs[:, None] < K)
        
        # Load and convert to float32
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        
        acc += tl.dot(a, b)
        
    # -----------------------------------------------------------
    # Store
    # -----------------------------------------------------------
    c_ptrs = C_batch_ptr + (offs_am[:, None] * stride_cm) + (offs_bn[None, :] * stride_cn)
    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K)
        B: Input tensor of shape (B, K, N)
    
    Returns:
        Output tensor of shape (B, M, N)
    """
    assert A.is_cuda and B.is_cuda
    Batch, M, K = A.shape
    _, _, N = B.shape
    
    # Output tensor
    C = torch.empty((Batch, M, N), device=A.device, dtype=torch.float16)
    
    # Grid: (Spatial, Batch)
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        Batch
    )
    
    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(1), A.stride(2),
        B.stride(1), B.stride(2),
        C.stride(1), C.stride(2),
        A.stride(0), B.stride(0), C.stride(0)
    )
    
    return C
