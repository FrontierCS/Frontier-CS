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
    # Implements GELU activation: x * 0.5 * (1.0 + erf(x * 1/sqrt(2)))
    # Using tl.erf which is the standard intrinsic in Triton
    return x * 0.5 * (1.0 + tl.erf(x * 0.7071067811865476))

def get_configs():
    configs = []
    # Configurations optimized for L4 (Ada Lovelace architecture)
    # Covering a range of block sizes to handle various matrix shapes efficiently
    # Key params: BLOCK_M, BLOCK_N, BLOCK_K, num_stages, num_warps
    base_configs = [
        (128, 256, 64, 3, 8),
        (128, 128, 64, 3, 8),
        (128, 128, 32, 4, 4),
        (128, 64, 32, 4, 4),
        (64, 128, 32, 4, 4),
        (128, 32, 32, 4, 4),
        (64, 64, 32, 4, 4),
        (32, 32, 32, 2, 2)
    ]
    for bm, bn, bk, ns, nw in base_configs:
        configs.append(triton.Config(
            {'BLOCK_SIZE_M': bm, 'BLOCK_SIZE_N': bn, 'BLOCK_SIZE_K': bk, 'GROUP_SIZE_M': 8},
            num_stages=ns, num_warps=nw
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
    # PID mapping for better L2 cache hit rate via swizzling
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Compute offsets for the blocks
    offs_am = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_bn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    # Initial pointers
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Accumulator in float32 for precision
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Main loop over K dimension
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Calculate mask for K dimension to handle arbitrary K sizes
        # We need to ensure we don't load out of bounds in K
        k_remaining = K - k * BLOCK_SIZE_K
        k_mask = offs_k < k_remaining
        
        # Combined masks for A and B
        # A: [BLOCK_M, BLOCK_K] -> Mask rows < M, cols < k_remaining
        # B: [BLOCK_K, BLOCK_N] -> Mask rows < k_remaining, cols < N
        a_mask = (offs_am[:, None] < M) & k_mask[None, :]
        b_mask = k_mask[:, None] & (offs_bn[None, :] < N)
        
        # Load blocks with masking and zero padding
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        
        # Matrix multiplication
        accumulator += tl.dot(a, b)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Apply GELU activation
    c = gelu(accumulator)

    # Store result with masking for M and N boundaries
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Check constraints
    M, K = a.shape
    K2, N = b.shape
    assert K == K2, f"Incompatible dimensions: {a.shape} and {b.shape}"
    
    # Allocate output tensor
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Launch grid
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
        return {"code": code}
