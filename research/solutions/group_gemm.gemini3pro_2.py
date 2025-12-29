import torch
import triton
import triton.language as tl
from typing import Dict, Optional
from pathlib import Path

# Configs optimized for L4 (Ada Lovelace)
# We include configs for both large and small matrix sizes to handle various M, N, K
@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    # Pointers
    A_ptr, B_ptr, C_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program IDs
    pid = tl.program_id(axis=0)
    batch_id = tl.program_id(axis=1)

    # -----------------------------------------------------------
    # Map pid to spatial blocks (swizzling for L2 cache efficiency)
    # -----------------------------------------------------------
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # -----------------------------------------------------------
    # Memory Pointers and Offsets
    # -----------------------------------------------------------
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Base pointers for the current batch
    A_batch_ptr = A_ptr + batch_id * stride_ab
    B_batch_ptr = B_ptr + batch_id * stride_bb
    C_batch_ptr = C_ptr + batch_id * stride_cb

    # Initialize accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # -----------------------------------------------------------
    # K-loop
    # -----------------------------------------------------------
    for k in range(0, K, BLOCK_K):
        # Calculate current K indices
        k_idxs = k + offs_k
        
        # Calculate pointers for the current block
        # Broadcasting to create (BLOCK_M, BLOCK_K) and (BLOCK_K, BLOCK_N) pointer matrices
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)
        
        # Boundary masking
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        
        # Load and cast to float32 for accumulation
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        
        # Accumulate
        acc += tl.dot(a, b)

    # -----------------------------------------------------------
    # Store result
    # -----------------------------------------------------------
    c = acc.to(tl.float16)
    
    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    tl.store(C_ptrs, c, mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication using Triton.
    Args:
        A: (B, M, K) tensor
        B: (B, K, N) tensor
    Returns:
        C: (B, M, N) tensor
    """
    assert A.dim() == 3 and B.dim() == 3, "Input tensors must be 3-dimensional"
    assert A.shape[0] == B.shape[0], "Batch dimension must match"
    assert A.shape[2] == B.shape[1], "Incompatible matrix dimensions for multiplication"
    
    Batch, M, K = A.shape
    _, _, N = B.shape
    
    # Allocate output tensor
    C = torch.empty((Batch, M, N), device=A.device, dtype=torch.float16)
    
    # 1D grid for spatial dimensions (handled by swizzling in kernel), Batch dimension in grid Z
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        Batch
    )
    
    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2)
    )
    
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        return {"code": Path(__file__).resolve().read_text(encoding="utf-8")}