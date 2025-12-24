import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional

# Autotuning configurations for different matrix sizes
# Optimized for NVIDIA L4 and diverse batch sizes/dimensions
@triton.autotune(
    configs=[
        # Larger blocks for larger matrices
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        # Balanced blocks for medium matrices (e.g. 64x64)
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        # Deep K blocks
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        # Small blocks for small matrices
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_Ab, stride_Am, stride_Ak,
    stride_Bb, stride_Bk, stride_Bn,
    stride_Cb, stride_Cm, stride_Cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    # Program ID
    pid = tl.program_id(axis=0)
    pid_batch = tl.program_id(axis=2)
    
    # Number of blocks along M and N
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    
    # Swizzling for better L2 cache hit rate
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Compute memory offsets for this batch
    offs_batch_a = pid_batch * stride_Ab
    offs_batch_b = pid_batch * stride_Bb
    offs_batch_c = pid_batch * stride_Cb

    # Compute block offsets for M and N dimensions
    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M))
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N))
    
    # Pointers to the start of the batch for A and B
    # A has shape (B, M, K), B has shape (B, K, N)
    # We add the batch offset and the M/N dimension offset
    # A_ptr_base points to A[b, m_start:m_end, 0]
    A_ptr_base = A_ptr + offs_batch_a + (offs_am[:, None] * stride_Am)
    # B_ptr_base points to B[b, 0, n_start:n_end]
    B_ptr_base = B_ptr + offs_batch_b + (offs_bn[None, :] * stride_Bn)

    # Accumulator for matrix multiplication (Float32 for precision)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Masks for A and B boundaries (M and N dimensions)
    # Ensure we don't access out of bounds if M/N are not multiples of BLOCK_M/BLOCK_N
    mask_m = offs_am < M
    mask_n = offs_bn < N

    # Loop over K dimension
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Offsets in K dimension
        k_val = k * BLOCK_K
        offs_k = k_val + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K
        
        # Calculate pointers for the current K block
        # A: (BLOCK_M, BLOCK_K) tile
        a_ptrs = A_ptr_base + (offs_k[None, :] * stride_Ak)
        # B: (BLOCK_K, BLOCK_N) tile
        b_ptrs = B_ptr_base + (offs_k[:, None] * stride_Bk)
        
        # Load tiles with boundary checks
        # We need to broadcast the masks to 2D
        load_mask_a = mask_m[:, None] & mask_k[None, :]
        load_mask_b = mask_n[None, :] & mask_k[:, None]
        
        # Load in original dtype (likely float16) and convert to float32 before accumulation
        a = tl.load(a_ptrs, mask=load_mask_a, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=load_mask_b, other=0.0).to(tl.float32)
        
        # Accumulate
        acc += tl.dot(a, b)

    # Store result
    # C has shape (B, M, N)
    c_ptrs = C_ptr + offs_batch_c + (offs_am[:, None] * stride_Cm) + (offs_bn[None, :] * stride_Cn)
    store_mask = mask_m[:, None] & mask_n[None, :]
    
    # Convert accumulator back to float16
    tl.store(c_ptrs, acc.to(tl.float16), mask=store_mask)

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
    assert A.is_cuda and B.is_cuda
    assert A.dim() == 3 and B.dim() == 3
    batch_a, M, K = A.shape
    batch_b, K_b, N = B.shape
    assert batch_a == batch_b
    assert K == K_b
    
    # Allocation
    C = torch.empty((batch_a, M, N), device=A.device, dtype=torch.float16)
    
    # Strides
    stride_Ab, stride_Am, stride_Ak = A.stride()
    stride_Bb, stride_Bk, stride_Bn = B.stride()
    stride_Cb, stride_Cm, stride_Cn = C.stride()
    
    # Kernel Launch
    # Grid handles B dimension as Z-axis
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
        1,
        batch_a
    )
    
    bmm_kernel[grid](
        A, B, C,
        M, N, K,
        stride_Ab, stride_Am, stride_Ak,
        stride_Bb, stride_Bk, stride_Bn,
        stride_Cb, stride_Cm, stride_Cn
    )
    
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
