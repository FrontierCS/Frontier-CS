import torch
import triton
import triton.language as tl
from typing import Dict, Optional
from pathlib import Path

# The bmm function must be in the module's global namespace
_bmm_kernel = None

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 2}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    M, N, K,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    """
    Triton kernel for batched matrix multiplication.
    Each program instance computes a BLOCK_M x BLOCK_N block of the output matrix C.
    The grid is 3D, with the third dimension being the batch dimension.
    """
    # Get the program IDs for the M, N, and batch dimensions
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    pid_b = tl.program_id(axis=2)

    # Compute offsets for the M and N dimensions for this program instance
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Offsets for the K dimension, used inside the loop
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers to the start of the matrices for the current batch
    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb
    C_batch_ptr = C_ptr + pid_b * stride_cb

    # Initialize accumulator with zeros. Use float32 for higher precision.
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over the K dimension in blocks of BLOCK_K
    # This is the main loop for the matrix multiplication
    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        
        # Pointers to the current block of A and B
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)
        
        # Create masks to handle boundary conditions (M, N, K not divisible by block sizes)
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)
        
        # Load A and B blocks from memory, applying masks
        # Convert to float32 before accumulation
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        
        # Perform matrix multiplication for the current block and accumulate
        acc += tl.dot(a, b)
        
        # Advance to the next block in the K dimension
        k0 += BLOCK_K

    # Pointers to the output block in C
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    C_ptrs = C_batch_ptr + (offs_cm[:, None] * stride_cm) + (offs_cn[None, :] * stride_cn)
    
    # Create mask for storing the output block
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    # Store the result in C, casting back to the output dtype (float16)
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K) - batch of M×K matrices
        B: Input tensor of shape (B, K, N) - batch of K×N matrices
    
    Returns:
        Output tensor of shape (B, M, N) - batch of M×N result matrices
    """
    # Input validation
    assert A.shape[0] == B.shape[0], "Batch dimensions must match"
    assert A.shape[2] == B.shape[1], "Inner dimensions must match (K)"
    assert A.is_cuda and B.is_cuda, "Inputs must be on GPU"
    assert A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"

    # Get dimensions
    Batches, M, K = A.shape
    _, _, N = B.shape

    # Create output tensor
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    # Define the grid for the kernel launch
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
        Batches
    )

    # Launch the Triton kernel
    _bmm_kernel[grid](
        A, B, C,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
        M, N, K,
    )
    
    return C

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
