import torch
import triton
import triton.language as tl
from typing import Dict, Optional

@triton.autotune(
    configs=[
        # Basic configurations for common sizes
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 16, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 2}),
        
        # High-performance configurations
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        
        # Larger block size configurations (autotuner will prune if not applicable)
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
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
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    """
    Triton kernel for batched matrix multiplication.
    Each program instance computes a BLOCK_M x BLOCK_N block of the output matrix C
    for a given batch index.
    """
    # Get the program IDs for the M, N, and Batch dimensions.
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    pid_b = tl.program_id(axis=2)

    # Compute offsets for the current block in M and N dimensions.
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Create offsets for the K dimension.
    offs_k = tl.arange(0, BLOCK_K)

    # Initialize pointers to the start of the A and B matrices for the current batch.
    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb

    # Initialize accumulator with zeros. Use float32 for higher precision and stability.
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Main loop over the K dimension.
    k_start = 0
    while k_start < K:
        # Compute pointers to the current blocks of A and B.
        k_idxs = k_start + offs_k
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        # Create masks to handle boundary conditions for M and K dimensions for A.
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        # Create masks to handle boundary conditions for K and N dimensions for B.
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        # Load data from A and B, applying masks. `other=0.0` handles out-of-bounds.
        # Convert loaded data to float32 before accumulation.
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        # Perform matrix multiplication for the current blocks and accumulate the result.
        acc += tl.dot(a, b)

        # Advance to the next block in the K dimension.
        k_start += BLOCK_K

    # Compute pointers to the output C matrix for the current batch.
    C_batch_ptr = C_ptr + pid_b * stride_cb
    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)

    # Create a mask for storing the final result to C.
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    # Store the result. Cast accumulator to float16 before storing.
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
    # Input validation.
    assert A.shape[0] == B.shape[0], "Batch dimensions must match"
    assert A.shape[2] == B.shape[1], "Inner dimensions must match"
    assert A.is_cuda and B.is_cuda, "Input tensors must be on CUDA device"
    assert A.dtype == torch.float16 and B.dtype == torch.float16, "Input tensors must be float16"

    # Get matrix dimensions.
    Batches, M, K = A.shape
    _, _, N = B.shape

    # Create the output tensor. Output dtype must be float16.
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    # Define the grid for launching the kernel.
    # The grid is 3D, with dimensions corresponding to M, N, and Batch tiles.
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']), Batches)

    # Launch the Triton kernel.
    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
    )

    return C

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        from pathlib import Path
        # Read the source code of the current file.
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}