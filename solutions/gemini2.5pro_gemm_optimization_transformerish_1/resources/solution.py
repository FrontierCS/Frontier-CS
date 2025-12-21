import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    """
    GELU activation function as required by the problem spec.
    Uses `erf` from libdevice for precision.
    """
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        # Basic configurations for a variety of shapes
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        
        # Configurations with larger K blocks for better data reuse
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 256, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 256, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),

        # Configurations with smaller block sizes for potential occupancy improvements
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 5, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 256, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_kernel_gelu(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    """
    Triton kernel for matrix multiplication with fused GELU activation.
    - Tiling is used to load data into SRAM.
    - Autotuning finds the best tile sizes and scheduling.
    - Grouping of thread blocks improves L2 cache locality.
    - Masking handles matrix dimensions that are not multiples of tile sizes.
    """
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    # Grouping for L2 cache performance
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size)
    pid_n = (pid % num_pid_in_group) // group_size

    # Pointers to the start of the blocks that this program will handle
    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M))
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N))
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    a_ptrs = A + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Accumulator for the C tile, initialized to zeros
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Pre-calculate masks for M and N dimensions
    m_mask = offs_am < M
    n_mask = offs_bn < N

    # Loop over the K dimension
    for k in range(0, K, BLOCK_SIZE_K):
        k_rem = K - k
        k_mask = offs_k < k_rem

        # Load tiles from A and B with boundary checks
        a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
        b = tl.load(b_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
        
        # Matrix multiply-accumulate
        accumulator += tl.dot(a, b)
        
        # Advance pointers to the next K block
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Convert accumulator to output dtype and apply GELU
    c = accumulator.to(C.dtype.element_ty)
    c = gelu(c)

    # Write back the result tile to C
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = C + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    
    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)
    
    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    """
    M, K = a.shape
    K_b, N = b.shape
    if K != K_b:
        raise ValueError("Input matrix dimensions do not match for multiplication")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Input tensors must be on CUDA device")
    
    # Use float16 for high performance on NVIDIA L4 GPU.
    # The loose tolerance (rtol=1e-2, atol=5e-3) allows for this optimization.
    a_fp16 = a if a.dtype == torch.float16 else a.to(torch.float16)
    b_fp16 = b if b.dtype == torch.float16 else b.to(torch.float16)

    c = torch.empty((M, N), device=a.device, dtype=a_fp16.dtype)

    # Define the grid for kernel launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),)
    
    _matmul_kernel_gelu[grid](
        a_fp16, b_fp16, c,
        M, N, K,
        a_fp16.stride(0), a_fp16.stride(1),
        b_fp16.stride(0), b_fp16.stride(1),
        c.stride(0), c.stride(1),
    )
    return c

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict indicating the path to the program file.
        The evaluator is expected to find the `matmul` function in this file.
        """
        return {"program_path": __file__}
