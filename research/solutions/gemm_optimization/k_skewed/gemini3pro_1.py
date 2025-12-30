import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    """
    GELU activation function: 0.5 * x * (1 + erf(x / sqrt(2)))
    """
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def get_autotune_config():
    """
    Generate a list of Autotune configs for the GEMM kernel.
    Optimized for L4 (Ada Lovelace) architecture.
    """
    configs = []
    # (BLOCK_M, BLOCK_N, BLOCK_K, num_stages, num_warps)
    # Balanced configurations for various shapes
    settings = [
        # Large tiles for high throughput on large M, N
        (128, 128, 32, 3, 8),
        (128, 64, 32, 4, 4),
        (64, 128, 32, 4, 4),
        (64, 64, 32, 4, 4),
        
        # Larger K tiles for Huge K (High arithmetic intensity)
        (128, 64, 64, 3, 4),
        (64, 128, 64, 3, 4),
        (64, 64, 64, 3, 4),
        (32, 32, 64, 2, 4),
        
        # Smaller tiles for small M/N or odd shapes
        (32, 32, 32, 2, 4),
        (16, 16, 32, 2, 4),
        
        # Aggressive configs
        (128, 128, 32, 2, 8),
        (128, 256, 32, 2, 8),
        (256, 128, 32, 2, 8),
    ]
    
    for (bm, bn, bk, ns, nw) in settings:
        configs.append(triton.Config(
            {'BLOCK_SIZE_M': bm, 'BLOCK_SIZE_N': bn, 'BLOCK_SIZE_K': bk, 'GROUP_SIZE_M': 8},
            num_stages=ns, num_warps=nw
        ))
    return configs

@triton.autotune(
    configs=get_autotune_config(),
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
    # Map program IDs to the block of C
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    # Swizzle for L2 cache data reuse
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Create pointers for the first blocks of A and B
    # We use real indices for masking
    offs_am = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_bn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Pointer arithmetic
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Accumulator
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Loop over K
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Calculate mask for K dimension (handling boundaries)
        # The offset in K is k * BLOCK_SIZE_K
        k_remaining = K - k * BLOCK_SIZE_K
        
        # Mask for loading A and B
        # A needs mask on M and K
        # B needs mask on K and N
        k_cond = offs_k < k_remaining
        
        a = tl.load(a_ptrs, mask=(offs_am[:, None] < M) & k_cond[None, :], other=0.0)
        b = tl.load(b_ptrs, mask=k_cond[:, None] & (offs_bn[None, :] < N), other=0.0)
        
        accumulator += tl.dot(a, b)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Activation: GELU
    c = gelu(accumulator)
    
    # Store result
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Validation
    assert a.shape[1] == b.shape[0], "Matrix dimensions mismatch"
    assert a.is_cuda and b.is_cuda, "Inputs must be on GPU"
    
    M, K = a.shape
    K, N = b.shape
    
    # Alloc output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Launch kernel
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), )
    
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1)
    )
    
    return c
"""
        return {"code": kernel_code}