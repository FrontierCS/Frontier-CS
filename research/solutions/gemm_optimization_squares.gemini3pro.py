import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    # GELU activation: 0.5 * x * (1 + erf(x / sqrt(2)))
    return x * 0.5 * (1.0 + tl.erf(x * 0.7071067811865476))

def get_configs():
    return [
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=2),
    ]

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
    GROUP_SIZE_M: tl.constexpr
):
    # PID mapping and L2 cache optimization (swizzling)
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Offset generation
    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M))
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N))
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Pointer arithmetic with 64-bit casting to avoid overflow on large inputs
    a_ptrs = a_ptr + (offs_am[:, None].to(tl.int64) * stride_am + offs_k[None, :].to(tl.int64) * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None].to(tl.int64) * stride_bk + offs_bn[None, :].to(tl.int64) * stride_bn)

    # Accumulator initialization (FP32)
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Main Loop
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Load A and B with masking for boundary conditions
        # Note: 'other=0.0' pads the masked values with zero, affecting neither sum nor boundaries
        a_vals = tl.load(a_ptrs, mask=(offs_am[:, None] < M) & (offs_k[None, :] + k * BLOCK_SIZE_K < K), other=0.0)
        b_vals = tl.load(b_ptrs, mask=(offs_k[:, None] + k * BLOCK_SIZE_K < K) & (offs_bn[None, :] < N), other=0.0)
        
        # Matrix Multiplication
        accumulator += tl.dot(a_vals, b_vals)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Fused GELU Activation
    accumulator = gelu(accumulator)
    
    # Store result
    c_ptrs = c_ptr + (offs_am[:, None].to(tl.int64) * stride_cm + offs_bn[None, :].to(tl.int64) * stride_cn)
    tl.store(c_ptrs, accumulator, mask=(offs_am[:, None] < M) & (offs_bn[None, :] < N))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Validation
    assert a.shape[1] == b.shape[0], "Matrix dimensions incompatible for multiplication"
    
    M, K = a.shape
    K, N = b.shape
    
    # Output buffer allocation
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Grid definition
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
        return {"code": code}