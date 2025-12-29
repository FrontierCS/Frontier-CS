import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    \"\"\"
    GELU activation function, as specified.
    \"\"\"
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
    ],
    key=['M', 'N', 'K', 'stride_am', 'stride_ak', 'stride_bk', 'stride_bn'],
)
@triton.jit
def _matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    \"\"\"
    Triton kernel for matrix multiplication with GELU activation.
    Each program instance computes a BLOCK_M x BLOCK_N tile of the output matrix C.
    \"\"\"
    # -----------------------------------------------------------
    # Map program ids to tiles
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # -----------------------------------------------------------
    # Create ranges for offsets
    # M-offsets for the program's tile
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    # N-offsets for the program's tile
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    # K-offsets for the inner loop
    offs_k = tl.arange(0, BLOCK_K)

    # -----------------------------------------------------------
    # Initialize pointers to A and B
    # These base pointers are for the top-left corner of the A and B tiles
    # that this program will access. The K dimension is handled in the loop.
    a_ptrs_base = a_ptr + offs_m[:, None] * stride_am
    b_ptrs_base = b_ptr + offs_n[None, :] * stride_bn

    # -----------------------------------------------------------
    # Accumulator for the C tile
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # -----------------------------------------------------------
    # Loop over K dimension
    for k in range(0, K, BLOCK_K):
        # Offsets for the current K-block
        k_offs = k + offs_k

        # Pointers to the current A and B tiles
        a_ptrs = a_ptrs_base + k_offs[None, :] * stride_ak
        b_ptrs = b_ptrs_base + k_offs[:, None] * stride_bk

        # Boundary checks for loading A and B tiles
        mask_a = (offs_m[:, None] < M) & (k_offs[None, :] < K)
        mask_b = (offs_n[None, :] < N) & (k_offs[:, None] < K)

        # Load A and B tiles, padding with 0.0 for out-of-bounds accesses
        a = tl.load(a_ptrs, mask=mask_a, other=0.0)
        b = tl.load(b_ptrs, mask=mask_b, other=0.0)

        # Perform the matrix multiplication for this tile
        accumulator += tl.dot(a, b)

    # -----------------------------------------------------------
    # Apply GELU and cast to output dtype
    c_with_gelu = gelu(accumulator)
    c_to_store = c_with_gelu.to(c_ptr.dtype.element_ty)

    # -----------------------------------------------------------
    # Write back the result
    # Pointers to the C tile
    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    # Boundary check for storing the C tile
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, c_to_store, mask=mask_c)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Matrix multiplication with GELU activation.
    
    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)
    
    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    \"\"\"
    # Input validation
    assert a.shape[1] == b.shape[0], "incompatible dimensions for matrix multiplication"
    assert a.is_cuda and b.is_cuda, "input tensors must be on a CUDA device"
    
    M, K = a.shape
    _, N = b.shape
    
    # Allocate the output tensor
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Define the grid for kernel launch
    # Each program instance computes one tile of the output matrix
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
    
    # Launch the kernel
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    
    return c
"""
        return {"code": kernel_code}