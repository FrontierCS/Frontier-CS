import torch
import triton
import triton.language as tl
from pathlib import Path

# Configuration for autotuning
# We define a set of configurations covering different tiling strategies.
# Smaller tiles for small matrices (like 64x64), larger tiles for larger matrices.
configs = [
    # Configs optimized for small shapes (target M=64, N=64)
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2),
    
    # Configs for larger shapes
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
]

@triton.autotune(
    configs=configs,
    key=['M', 'N', 'K']
)
@triton.jit
def _bmm_kernel(
    # Pointers
    A_ptr, B_ptr, C_ptr,
    # Dimensions
    M, N, K,
    # Strides
    stride_a_batch, stride_a_m, stride_a_k,
    stride_b_batch, stride_b_k, stride_b_n,
    stride_c_batch, stride_c_m, stride_c_n,
    # Metaparameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    """
    Batched Matrix Multiplication Kernel.
    Operates on batches of matrices A (MxK) and B (KxN) to produce C (MxN).
    """
    # -----------------------------------------------------------
    # Map Program ID to (Batch, Block_M, Block_N)
    # -----------------------------------------------------------
    # We use a 3D grid where:
    # axis 0: Linear index for spatial blocks (M, N)
    # axis 1: Unused (size 1)
    # axis 2: Batch dimension
    pid = tl.program_id(axis=0)
    pid_batch = tl.program_id(axis=2)
    
    # Swizzling logic to improve L2 cache locality (Grouped GEMM)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # -----------------------------------------------------------
    # Pointer Arithmetic
    # -----------------------------------------------------------
    # Calculate base pointers for the current batch
    a_batch_ptr = A_ptr + pid_batch * stride_a_batch
    b_batch_ptr = B_ptr + pid_batch * stride_b_batch
    c_batch_ptr = C_ptr + pid_batch * stride_c_batch

    # Create offsets for tiles
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Initialize accumulator in FP32 for numerical stability
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # -----------------------------------------------------------
    # Main Loop
    # -----------------------------------------------------------
    # Iterate over K dimension in chunks of BLOCK_K
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Calculate current K indices
        # We need this for mask and pointer calculation
        k_val = k * BLOCK_K
        k_idxs = k_val + offs_k
        
        # Calculate masks to handle shapes not divisible by block size
        # Check boundaries for M, N, and K
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        # Calculate pointers for the current K-block
        # Formula: Base + (Row * Stride_Row) + (Col * Stride_Col)
        a_ptrs = a_batch_ptr + (offs_m[:, None] * stride_a_m) + (k_idxs[None, :] * stride_a_k)
        b_ptrs = b_batch_ptr + (k_idxs[:, None] * stride_b_k) + (offs_n[None, :] * stride_b_n)

        # Load data, converting to FP32 for accumulation
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        # Matrix multiplication accumulation
        accumulator = tl.dot(a, b, accumulator)

    # -----------------------------------------------------------
    # Store Result
    # -----------------------------------------------------------
    # Convert accumulator back to FP16 for output
    c = accumulator.to(tl.float16)
    
    # Calculate output pointers
    c_ptrs = c_batch_ptr + (offs_m[:, None] * stride_c_m) + (offs_n[None, :] * stride_c_n)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    tl.store(c_ptrs, c, mask=c_mask)

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
    assert A.is_cuda and B.is_cuda, "Inputs must be on GPU"
    assert A.ndim == 3 and B.ndim == 3, "Inputs must be 3D tensors"
    assert A.shape[0] == B.shape[0], "Batch dimension mismatch"
    assert A.shape[2] == B.shape[1], "Inner dimension mismatch (K)"

    Batches, M, K = A.shape
    _, _, N = B.shape

    # Output allocation (FP16)
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)
    
    # Grid definition: 
    # x: number of blocks in M * number of blocks in N (linearized)
    # y: 1
    # z: Batches
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        1,
        Batches
    )

    _bmm_kernel[grid](
        A, B, C,
        M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
    )

    return C

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the source code of the current file.
        """
        from pathlib import Path
        return {"code": Path(__file__).read_text(encoding="utf-8")}