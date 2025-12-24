import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    """
    GELU activation function using the error function.
    Matches the requirement: x * 0.5 * (1.0 + erf(x / sqrt(2)))
    """
    return x * 0.5 * (1.0 + tl.erf(x * 0.7071067811865476))

def get_configs():
    """
    Generate autotuning configurations for L4 (Ada Lovelace).
    Focus on block sizes and warp counts that align with Ada's strengths.
    """
    configs = []
    
    # Base configurations balancing occupancy and tile size
    # BLOCK_M, BLOCK_N, BLOCK_K, num_stages, num_warps
    settings = [
        (128, 128, 32, 3, 8),
        (128, 256, 32, 3, 8),
        (256, 128, 32, 3, 8),
        (64, 128, 32, 4, 4),
        (128, 64, 32, 4, 4),
        (64, 64, 32, 4, 4),
        (128, 128, 64, 3, 8),  # Larger K blocking
        (64, 64, 64, 4, 4)
    ]

    for (bm, bn, bk, stages, warps) in settings:
        configs.append(triton.Config(
            {'BLOCK_SIZE_M': bm, 'BLOCK_SIZE_N': bn, 'BLOCK_SIZE_K': bk, 'GROUP_SIZE_M': 8},
            num_stages=stages,
            num_warps=warps
        ))
    return configs

@triton.autotune(
    configs=get_configs(),
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
):
    """
    Triton kernel for General Matrix Multiplication with GELU activation.
    Features:
    - Block tiling for A and B
    - L2 Cache optimization via PID swizzling (Grouped execution)
    - Masking for handling arbitrary/awkward matrix shapes
    - GELU activation fused at the end
    """
    pid = tl.program_id(axis=0)
    
    # PID Swizzling / Grouping
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Offsets initialization
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    # Tensor Pointers
    # A is (M, K), B is (K, N)
    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    # Accumulator (FP32 for precision)
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Pre-calculate boundary masks for M and N dimensions
    # These remain constant throughout the K loop
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Main Loop over K
    # Using cdiv to ensure we cover the entire K dimension
    num_k_blocks = tl.cdiv(K, BLOCK_SIZE_K)
    
    for k in range(0, num_k_blocks):
        # Calculate mask for K dimension
        # This is necessary for "awkward" shapes where K is not a multiple of BLOCK_SIZE_K
        current_k_offs = k * BLOCK_SIZE_K + offs_k
        mask_k = current_k_offs < K
        
        # Load A and B with masking
        # A mask: (BLOCK_M, 1) & (1, BLOCK_K)
        load_mask_a = mask_m[:, None] & mask_k[None, :]
        a = tl.load(a_ptrs, mask=load_mask_a, other=0.0)
        
        # B mask: (BLOCK_K, 1) & (1, BLOCK_N)
        load_mask_b = mask_k[:, None] & mask_n[None, :]
        b = tl.load(b_ptrs, mask=load_mask_b, other=0.0)
        
        # Matrix Multiplication
        accumulator = tl.dot(a, b, accumulator)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Apply GELU activation
    c = gelu(accumulator)
    
    # Store result
    # We cast to result precision implicitly during store
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    
    c_mask = mask_m[:, None] & mask_n[None, :]
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
    # Validation
    assert a.dim() == 2 and b.dim() == 2, "Tensors must be 2-dimensional"
    assert a.shape[1] == b.shape[0], f"Shape mismatch: {a.shape} and {b.shape}"
    assert a.is_cuda and b.is_cuda, "Tensors must be on CUDA device"
    
    M, K = a.shape
    _, N = b.shape
    
    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Grid configuration
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), )
    
    # Kernel Launch
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1)
    )
    
    return c
"""
        }
