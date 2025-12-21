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
    # Implements GELU approximation: 0.5 * x * (1 + erf(x / sqrt(2)))
    # 1 / sqrt(2) approx 0.7071067811865476
    return x * 0.5 * (1.0 + tl.erf(x * 0.7071067811865476))

def get_autotune_config():
    configs = []
    # Configurations optimized for L4 GPU
    # Covering small K (skewed) and large GEMM cases
    for num_stages in [2, 3, 4]:
        for block_m in [32, 64, 128]:
            for block_n in [64, 128, 256]:
                for block_k in [32, 64]:
                    for num_warps in [4, 8]:
                        # Skip configs that use too many resources or are inefficient
                        if block_m * block_n < 2048 and num_warps == 8:
                            continue
                        configs.append(triton.Config(
                            {'BLOCK_SIZE_M': block_m, 'BLOCK_SIZE_N': block_n, 'BLOCK_SIZE_K': block_k, 'GROUP_SIZE_M': 8},
                            num_stages=num_stages, num_warps=num_warps
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
    # PID mapping and L2 cache swizzling
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Offsets
    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M))
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N))
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    # Pointers
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # Accumulator
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Masks for M and N boundaries
    mask_m = offs_am < M
    mask_n = offs_bn < N

    # Loop over K
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Mask for K boundary
        current_k = k * BLOCK_SIZE_K
        mask_k = (current_k + offs_k) < K
        
        # Load blocks with masking (zero padding)
        a = tl.load(a_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
        b = tl.load(b_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
        
        # Accumulate
        accumulator += tl.dot(a, b)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_ak
        b_ptrs += BLOCK_SIZE_K * stride_bk

    # Apply GELU activation
    c = gelu(accumulator)

    # Store result
    offs_cm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    # Store with implicit cast to output dtype
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Validation
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    M, K = a.shape
    _, N = b.shape
    
    # Allocating output with same dtype as input
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Grid definition
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), )
    
    # Launch kernel
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
