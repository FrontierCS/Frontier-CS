import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional

@triton.autotune(
    configs=[
        # Basic configurations for M,N,K=64
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        
        # Wider tiles
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
        
        # Taller tiles
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 2}),

        # Configurations with more warps
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),

        # Fallback small config
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 2}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    Batches, M, N, K,
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
    # Get program IDs for batch, M, and N dimensions
    pid_batch = tl.program_id(axis=0)
    pid_m = tl.program_id(axis=1)
    pid_n = tl.program_id(axis=2)

    # Compute offsets for the current block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers to the start of the matrices for the current batch
    A_batch_ptr = A_ptr + pid_batch * stride_ab
    B_batch_ptr = B_ptr + pid_batch * stride_bb

    # Initialize accumulator with zeros in float32 for precision
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over the K dimension in blocks of BLOCK_K
    k0 = 0
    while k0 < K:
        # Offsets for the current K block
        k_idxs = k0 + offs_k
        
        # Pointers to the current blocks in A and B
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        # Create masks to handle matrix dimensions that are not multiples of block sizes
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        
        # Load A and B blocks from global memory
        # Apply masks and pad with 0.0 for out-of-bounds accesses
        a = tl.load(A_ptrs, mask=a_mask, other=0.0)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0)
        
        # Cast inputs to float32 before dot product
        # Accumulate in float32
        accumulator += tl.dot(a.to(tl.float32), b.to(tl.float32))
        
        # Advance to the next block in the K dimension
        k0 += BLOCK_K

    # Pointer to the start of the output matrix for the current batch
    C_batch_ptr = C_ptr + pid_batch * stride_cb
    # Pointers to the output block in C
    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    
    # Create a mask for storing the final result to C
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    # Cast accumulator to float16 and store the result
    tl.store(C_ptrs, accumulator.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K) - batch of M×K matrices
        B: Input tensor of shape (B, K, N) - batch of K×N matrices
    
    Returns:
        Output tensor of shape (B, M, N) - batch of M×N result matrices
    """
    # Basic shape and device checks
    assert A.shape[0] == B.shape[0], "Batch dimensions of A and B must match"
    assert A.shape[2] == B.shape[1], "Inner dimensions of A and B must match (K)"
    assert A.is_cuda and B.is_cuda, "Input tensors must be on a CUDA device"

    Batches, M, K = A.shape
    _, _, N = B.shape

    # The output tensor is float16 as required.
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    # Define the grid for the kernel launch.
    # Each program in the grid computes one block of the output matrix.
    # The grid is 3-dimensional: (Batch, Ceil(M/BLOCK_M), Ceil(N/BLOCK_N))
    grid = lambda meta: (Batches, triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

    # Launch the Triton kernel.
    _bmm_kernel[grid](
        A, B, C,
        Batches, M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
    )
    
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        """
        Returns a dict with the Python code for the bmm kernel.
        """
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}