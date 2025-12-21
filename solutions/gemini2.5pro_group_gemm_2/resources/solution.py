import torch
import triton
import triton.language as tl
from typing import Dict
from pathlib import Path

@triton.autotune(
    configs=[
        # Basic configurations for small matrix sizes (e.g., 64x64)
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_warps': 2, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128, 'num_warps': 2, 'num_stages': 2}),

        # Configurations with larger block sizes for general-purpose use
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 8, 'num_stages': 3}),

        # Configurations inspired by Triton tutorials and common practices
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
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
    for a single batch item.
    """
    # Get program IDs for batch, M, and N dimensions
    pid_batch = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_n = tl.program_id(2)

    # Compute offsets for the C block this program will write
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Initialize pointers to the start of the A and B matrices for the current batch
    A_batch_ptr = A_ptr + pid_batch * stride_ab
    B_batch_ptr = B_ptr + pid_batch * stride_bb

    # Initialize accumulator with zeros. Use tl.float32 for precision.
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over the K dimension of A and B in chunks of BLOCK_K
    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        # Pointers for A tile (BLOCK_M x BLOCK_K)
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak)
        # Pointers for B tile (BLOCK_K x BLOCK_N)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        # Create masks for safe loading from A and B
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        # Load A and B tiles with masking, padding with 0.0
        a = tl.load(A_ptrs, mask=a_mask, other=0.0)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0)

        # Convert loaded tiles to float32 before dot product
        a = a.to(tl.float32)
        b = b.to(tl.float32)
        
        # Perform matrix multiplication for the tiles and accumulate
        acc += tl.dot(a, b)
        
        # Advance to the next K block
        k0 += BLOCK_K

    # Calculate pointers to the C block
    C_batch_ptr = C_ptr + pid_batch * stride_cb
    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    
    # Create mask for storing the C block
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    # Store the result block in C, casting accumulator to float16
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
    # Basic input validation
    assert A.shape[0] == B.shape[0], "Batch dimensions must match"
    assert A.shape[2] == B.shape[1], "Inner dimensions K must match"
    assert A.is_cuda and B.is_cuda, "Input tensors must be on a CUDA device"
    
    Batches, M, K = A.shape
    _, _, N = B.shape
    
    # Create output tensor C with the required float16 dtype
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    # Grid definition function to be used by the kernel launcher
    def grid(meta):
        return (Batches, triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))
        
    # Launch the Triton kernel
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
        # This method reads the entire content of the current Python file
        # and returns it as a string, which is the required submission format.
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
