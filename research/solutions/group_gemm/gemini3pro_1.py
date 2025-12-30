import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Optional, Dict

# Autotune configurations
# Optimized for NVIDIA L4 (Ada Lovelace)
# We prioritize configurations that align well with 64x64x64 shapes while providing scalability for larger shapes.
configs = [
    # Configurations for larger matrices
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
    
    # Configurations optimized for the default 64x64x64 case (1 block, no loop overhead if K=64)
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
    
    # Configurations for smaller matrices or leftovers
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64}, num_stages=2, num_warps=2),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_stages=2, num_warps=2),
    triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 32}, num_stages=2, num_warps=2),
]

@triton.autotune(
    configs=configs,
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    # Pointers
    A_ptr, B_ptr, C_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_Am, stride_Ak, stride_Ab,  # A: (M, K, Batch) in terms of strides if using PyTorch defaults
    stride_Bk, stride_Bn, stride_Bb,  # B: (K, N, Batch)
    stride_Cm, stride_Cn, stride_Cb,  # C: (M, N, Batch)
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    """
    Batched Matrix Multiplication Kernel
    Computes C[b] = A[b] @ B[b] for a batch of matrices.
    """
    # Program IDs
    pid_batch = tl.program_id(2)
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    # -----------------------------------------------------------
    # 1. Pointer Arithmetic
    # -----------------------------------------------------------
    # Calculate base pointers for the current batch
    # A_ptr/B_ptr/C_ptr are the start of the entire tensor data
    A_batch_ptr = A_ptr + (pid_batch * stride_Ab)
    B_batch_ptr = B_ptr + (pid_batch * stride_Bb)
    C_batch_ptr = C_ptr + (pid_batch * stride_Cb)

    # Offsets for the block dimensions M and N
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Offsets for the accumulation dimension K (start at 0)
    offs_k = tl.arange(0, BLOCK_K)

    # Initialize accumulator
    # Accumulate in float32 for numerical stability
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # -----------------------------------------------------------
    # 2. Main Loop
    # -----------------------------------------------------------
    # Iterate over K dimension in chunks of BLOCK_K
    for k in range(0, K, BLOCK_K):
        # Calculate current K indices
        k_idxs = k + offs_k

        # Calculate pointers for the current block
        # A: Shape (M, K) -> Indexing: (offs_m, k_idxs)
        # B: Shape (K, N) -> Indexing: (k_idxs, offs_n)
        # Note: We compute the full pointer here as per recommended pattern for clarity and correctness with strides
        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_Am) + (k_idxs[None, :] * stride_Ak)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_Bk) + (offs_n[None, :] * stride_Bn)

        # Boundary masks
        # A mask: Ensure we are within M bounds and K bounds
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        # B mask: Ensure we are within K bounds and N bounds
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        # Load data
        # Must cast to float32 before dot product as per requirements/best practice for this problem
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        # Compute dot product
        acc += tl.dot(a, b)

    # -----------------------------------------------------------
    # 3. Store Result
    # -----------------------------------------------------------
    # Calculate output pointers
    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_Cm) + (offs_n[None, :] * stride_Cn)
    
    # Output mask (M and N bounds)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    # Cast to float16 for output
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K) - batch of M×K matrices
        B: Input tensor of shape (B, K, N) - batch of K×N matrices
    
    Returns:
        Output tensor of shape (B, M, N) - batch of M×N result matrices
    """
    # Validation
    assert A.ndim == 3 and B.ndim == 3, "Inputs must be 3D tensors"
    assert A.shape[0] == B.shape[0], "Batch dimension must match"
    assert A.shape[2] == B.shape[1], "K dimension must match"

    Batch, M, K = A.shape
    _, _, N = B.shape

    # Allocate output tensor (float16)
    C = torch.empty((Batch, M, N), device=A.device, dtype=torch.float16)

    # Grid definition: (M_blocks, N_blocks, Batch_size)
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
        Batch
    )

    # Launch kernel
    # Passing specific strides allows handling of non-contiguous tensors
    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(1), A.stride(2), A.stride(0),  # stride_Am, stride_Ak, stride_Ab
        B.stride(1), B.stride(2), B.stride(0),  # stride_Bk, stride_Bn, stride_Bb
        C.stride(1), C.stride(2), C.stride(0)   # stride_Cm, stride_Cn, stride_Cb
    )

    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        """
        Returns the solution code.
        """
        return {"code": Path(__file__).read_text(encoding="utf-8")}