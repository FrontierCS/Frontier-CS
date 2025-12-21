import torch
import triton
import triton.language as tl
from typing import Dict, Optional
from pathlib import Path

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    # Program IDs
    pid = tl.program_id(axis=0)
    batch_id = tl.program_id(axis=1)

    # Number of blocks along M and N
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    
    # Swizzling for better L2 cache locality
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Batch offsets
    A_batch_ptr = A_ptr + batch_id * stride_ab
    B_batch_ptr = B_ptr + batch_id * stride_bb
    C_batch_ptr = C_ptr + batch_id * stride_cb

    # Block offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers for the first block
    A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    B_ptrs = B_batch_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    # Accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over K
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_val = k * BLOCK_K + offs_k
        
        # Masking for boundary conditions
        a_mask = (offs_m[:, None] < M) & (k_val[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_val[:, None] < K)
        
        # Load and cast to fp32 (required by problem spec)
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        
        # Accumulate
        acc += tl.dot(a, b)
        
        # Advance pointers
        A_ptrs += BLOCK_K * stride_ak
        B_ptrs += BLOCK_K * stride_bk

    # Store result
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    C_ptrs = C_batch_ptr + (offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn)
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    # Cast to fp16 before storing
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K)
        B: Input tensor of shape (B, K, N)
    
    Returns:
        Output tensor of shape (B, M, N)
    """
    # Validation
    assert A.ndim == 3 and B.ndim == 3, "A and B must be 3D tensors"
    assert A.shape[0] == B.shape[0], "Batch dimension must match"
    assert A.shape[2] == B.shape[1], "K dimension must match"
    
    Batches, M, K = A.shape
    _, _, N = B.shape
    
    # Output tensor
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)
    
    # Grid definition: (M blocks * N blocks, Batches)
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        Batches
    )
    
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
        """
        Returns a dict with the source code of the current file.
        """
        return {"code": Path(__file__).resolve().read_text(encoding="utf-8")}
