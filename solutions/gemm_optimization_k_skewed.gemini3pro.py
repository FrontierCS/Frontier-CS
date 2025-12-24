import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

# Helper to handle libdevice import across Triton versions
try:
    from triton.language import libdevice
except ImportError:
    try:
        from triton.language.extra.cuda import libdevice
    except ImportError:
        # Fallback for very new or specific environments
        import triton.language.math as libdevice

@triton.jit
def gelu(x):
    """
    Applies GELU activation: 0.5 * x * (1 + erf(x / sqrt(2)))
    Using the constant 1/sqrt(2) approx 0.7071067811865476
    """
    return x * 0.5 * (1.0 + libdevice.erf(x * 0.7071067811865476))

def get_configs():
    configs = []
    # Configs optimized for small K (e.g. K=32, 64)
    # Reduced stage count as deep pipelines aren't filled
    configs.append(triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=2))
    configs.append(triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=4))
    configs.append(triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=2, num_warps=4))
    
    # Configs optimized for large K (e.g. K=4096+)
    # Larger block sizes and pipelining
    for blk_m in [64, 128]:
        for blk_n in [128, 256]:
            for blk_k in [64, 128]:
                for stages in [3, 4]:
                    for warps in [4, 8]:
                        configs.append(triton.Config(
                            {'BLOCK_SIZE_M': blk_m, 'BLOCK_SIZE_N': blk_n, 'BLOCK_SIZE_K': blk_k, 'GROUP_SIZE_M': 8},
                            num_stages=stages, num_warps=warps
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
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Offsets for A and B
    offs_m = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M))
    offs_n = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N))
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Pointers
    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Masks for M and N dimensions
    mask_m = offs_m[:, None] < M
    mask_n = offs_n[None, :] < N
    
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Calculate remaining items in K dimension for masking
        k_remaining = K - k * BLOCK_SIZE_K
        
        # Mask for K dimension
        mask_k = offs_k < k_remaining
        
        # Load A and B with masking
        # A: (BLOCK_SIZE_M, BLOCK_SIZE_K)
        # B: (BLOCK_SIZE_K, BLOCK_SIZE_N)
        a = tl.load(a_ptrs, mask=mask_m & mask_k[None, :], other=0.0)
        b = tl.load(b_ptrs, mask=mask_k[:, None] & mask_n, other=0.0)
        
        accumulator += tl.dot(a, b)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk
        
    # Apply activation
    c = gelu(accumulator)
    
    # Store output
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Validation
    assert a.is_cuda and b.is_cuda, "Inputs must be on GPU"
    assert a.shape[1] == b.shape[0], "Dimension mismatch"
    
    M, K = a.shape
    _, N = b.shape
    
    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Launch kernel
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),
    )
    
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1)
    )
    
    return c
"""
        return {"code": code}
