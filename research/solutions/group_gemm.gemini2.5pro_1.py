import torch
import triton
import triton.language as tl
from typing import Dict, Optional
from pathlib import Path


class Solution:
    """
    Solution class for the Group GEMM Optimization Problem.
    """
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        """
        Returns the Python code for the Triton-based batched matrix multiplication.

        Args:
            spec_path (Optional[str]): Path to the problem specification. Not used.

        Returns:
            Dict[str, str]: A dictionary containing the source code.
        """
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}


# Autotuner configurations for the Triton kernel.
# These configurations are selected to cover a range of tile sizes and warp/stage counts
# to find the optimal settings for various matrix dimensions.
_bmm_configs = [
    # Basic configurations for common sizes (e.g., M=N=K=64)
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4}),
    
    # Configurations with larger tile sizes
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    
    # Configurations with smaller tile sizes for better occupancy on smaller problems
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),

    # More aggressive configurations
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
]


@triton.autotune(
    configs=_bmm_configs,
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A, B, C,
    M, N, K,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    """
    Triton kernel for batched matrix multiplication.
    Each program instance computes a BLOCK_M x BLOCK_N tile of the output matrix C
    for a specific batch index.
    The grid is 3D: (Batch, CeilDiv(M, BLOCK_M), CeilDiv(N, BLOCK_N)).
    """
    # Get program IDs to identify the current batch, M-block, and N-block.
    pid_batch = tl.program_id(axis=0)
    pid_m = tl.program_id(axis=1)
    pid_n = tl.program_id(axis=2)

    # Compute offsets for the current block.
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Adjust pointers to the start of the current batch.
    A_batch_ptr = A + pid_batch * stride_ab
    B_batch_ptr = B + pid_batch * stride_bb
    C_batch_ptr = C + pid_batch * stride_cb

    # Initialize accumulator with zeros. Use tl.float32 for higher precision.
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over the K-dimension of A and B in blocks of BLOCK_K.
    # Using a while loop is more robust for JIT compilation with dynamic shapes.
    k_offset = 0
    while k_offset < K:
        # Define current k-slice offsets.
        k_idxs = k_offset + offs_k

        # Calculate pointers to the current blocks of A and B.
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        # Create masks to handle boundary conditions.
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        # Load blocks of A and B, applying masks to avoid out-of-bounds access.
        # Pad with 0.0 for masked-out elements.
        a = tl.load(A_ptrs, mask=a_mask, other=0.0)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0)

        # Convert loaded blocks to float32 before dot product for precision.
        # Accumulate the result in the float32 accumulator.
        accumulator += tl.dot(a.to(tl.float32), b.to(tl.float32))

        # Advance to the next block in the K-dimension.
        k_offset += BLOCK_K

    # Create pointers for storing the final result block in C.
    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    
    # Create a mask for storing to C to handle non-uniform M and N.
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    # Cast the accumulator to the output dtype (float16) and store.
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
    # Input validation
    assert A.is_cuda and B.is_cuda, "Input tensors must be on a CUDA device."
    assert A.dtype == torch.float16 and B.dtype == torch.float16, "Input tensors must have dtype torch.float16."
    assert A.dim() == 3 and B.dim() == 3, "Input tensors must be 3-dimensional."

    # Get dimensions
    Batches, M, K = A.shape
    _, K_b, N = B.shape
    assert K == K_b, f"Matrix dimensions are not compatible for multiplication: A({A.shape}), B({B.shape})"

    # Create the output tensor C with the required shape and dtype.
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    # Define the grid for launching the kernel.
    # The grid is 3D, corresponding to (Batch, M_blocks, N_blocks).
    grid = lambda META: (
        Batches,
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )

    # Launch the Triton kernel.
    # Pass tensors, dimensions, and strides as arguments.
    # The autotuner will select the best BLOCK_M, BLOCK_N, BLOCK_K.
    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2)
    )
    
    return C