import torch
import triton
import triton.language as tl
import inspect
import sys

# Required GELU implementation
@triton.jit
def gelu(x):
    """
    GeLU activation function, as specified in the problem.
    This is equivalent to x * Phi(x) where Phi is the standard normal CDF.
    """
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        # Basic configurations with varying block sizes and stages
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        # Configurations optimized for large K values
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 256, 'GROUP_SIZE_M': 16, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32,  'BLOCK_SIZE_K': 256, 'GROUP_SIZE_M': 16, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 32,  'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 256, 'GROUP_SIZE_M': 16, 'num_stages': 4, 'num_warps': 4}),
        # A simpler configuration without grouping as a fallback
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64,  'GROUP_SIZE_M': 1, 'num_stages': 2, 'num_warps': 4}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    num_stages: tl.constexpr,
):
    """
    Triton kernel for matrix multiplication with GeLU activation.
    This kernel uses tiling, software pipelining (via num_stages), and grouped
    scheduling to improve performance and L2 cache hit rate.
    """
    pid = tl.program_id(axis=0)
    grid_m = tl.cdiv(M, BLOCK_SIZE_M)
    grid_n = tl.cdiv(N, BLOCK_SIZE_N)

    # Re-order program IDs to improve L2 cache performance (grouped scheduling)
    width = GROUP_SIZE_M * grid_n
    group_id = pid // width
    group_size = min(grid_m - group_id * GROUP_SIZE_M, GROUP_SIZE_M)
    pid_m = group_id * GROUP_SIZE_M + (pid % group_size)
    pid_n = (pid % width) // group_size

    # Offsets for the M and N dimensions for the current block
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    # Offsets for the K dimension
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Initialize pointers to the A and B matrices for the first K-block
    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    # Initialize accumulator with float32 for precision
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Main loop over the K dimension, iterating in steps of BLOCK_SIZE_K
    for k in range(0, K, BLOCK_SIZE_K):
        # Define masks for the current K-block to handle edge cases
        k_offsets = k + offs_k
        a_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
        b_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)
        
        # Load tiles from A and B matrices from global memory
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        
        # Perform matrix multiplication on the tiles and accumulate the result
        accumulator += tl.dot(a, b, out_dtype=tl.float32)
        
        # Advance pointers to the next K-block
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Apply GELU activation to the accumulated result
    result = gelu(accumulator)
    
    # Cast the result to the output tensor's data type
    result = result.to(c_ptr.dtype.element_ty)

    # Initialize pointers to the C matrix
    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    
    # Write the final result back to global memory
    tl.store(c_ptrs, result, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    
    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)
    
    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    """
    # Check for compatibility of dimensions
    M, K = a.shape
    K_b, N = b.shape
    assert K == K_b, f"Incompatible dimensions: A has shape ({M}, {K}) and B has shape ({K_b}, {N})"

    # Create the output tensor on the same device as the inputs
    # The dtype is inferred from the inputs, which allows for fp16/bf16/fp32.
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    # Define the grid for launching the kernel
    # This uses a 1D grid, and the kernel internally computes 2D block IDs
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_SIZE_M']) * triton.cdiv(N, meta['BLOCK_SIZE_N']),)

    # Launch the Triton kernel
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    
    return c

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Python code for the matmul implementation.
        """
        # This method packages the entire file's source code to be sent
        # to the evaluation environment.
        return {"code": inspect.getsource(sys.modules[__name__])}
