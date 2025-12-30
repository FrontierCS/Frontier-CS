import torch
import triton
import triton.language as tl
from typing import Optional, Tuple


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K', 'STAGE_A', 'STAGE_B', 'EVEN_K', 'ACC_TYPE', 'OUT_TYPE',
         'stride_am', 'stride_ak', 'stride_bk', 'stride_bn']
)
@triton.jit
def _matmul_kernel(
    # Pointers to matrices
    A, B, C,
    # Matrix dimensions
    M, N, K,
    # Stride variables
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, SPLIT_K: tl.constexpr,
    EVEN_K: tl.constexpr, STAGE_A: tl.constexpr, STAGE_B: tl.constexpr,
    ACC_TYPE: tl.constexpr, OUT_TYPE: tl.constexpr,
):
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of C it should compute.
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # ----------------------------------------------------------
    # Create pointers for the first blocks of A and B.
    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)
    a_ptrs = A + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # -----------------------------------------------------------
    # Iterate to compute a block of the C matrix.
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    if STAGE_A == 3:
        a_ptrs = tl.make_block_ptr(base=A, shape=(M, K), strides=(stride_am, stride_ak),
                                   offsets=(pid_m * BLOCK_M, 0), block_shape=(BLOCK_M, BLOCK_K),
                                   order=(1, 0))
    if STAGE_B == 3:
        b_ptrs = tl.make_block_ptr(base=B, shape=(K, N), strides=(stride_bk, stride_bn),
                                   offsets=(0, pid_n * BLOCK_N), block_shape=(BLOCK_K, BLOCK_N),
                                   order=(0, 1))

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        if EVEN_K:
            if STAGE_A == 3:
                a = tl.load(a_ptrs, boundary_check=(0, 1))
                a_ptrs = tl.advance(a_ptrs, (0, BLOCK_K))
            else:
                a = tl.load(a_ptrs)
            if STAGE_B == 3:
                b = tl.load(b_ptrs, boundary_check=(0, 1))
                b_ptrs = tl.advance(b_ptrs, (BLOCK_K, 0))
            else:
                b = tl.load(b_ptrs)
        else:
            k_remaining = K - k * BLOCK_K
            if STAGE_A == 3:
                a = tl.load(a_ptrs, boundary_check=(0, 1))
                a_ptrs = tl.advance(a_ptrs, (0, BLOCK_K))
            else:
                a = tl.load(a_ptrs, mask=offs_k[None, :] < k_remaining, other=0.0)
            if STAGE_B == 3:
                b = tl.load(b_ptrs, boundary_check=(0, 1))
                b_ptrs = tl.advance(b_ptrs, (BLOCK_K, 0))
            else:
                b = tl.load(b_ptrs, mask=offs_k[:, None] < k_remaining, other=0.0)
        
        accumulator += tl.dot(a, b, out_dtype=ACC_TYPE)
        
        if STAGE_A != 3:
            a_ptrs += BLOCK_K * stride_ak
        if STAGE_B != 3:
            b_ptrs += BLOCK_K * stride_bk

    # Apply GELU activation
    accumulator = gelu(accumulator)
    
    # -----------------------------------------------------------
    # Write back the block of the output matrix C
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_ptrs = C + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    tl.store(c_ptrs, accumulator.to(OUT_TYPE), mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Check dimensions
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    M, K = a.shape
    K, N = b.shape
    
    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Heuristics for better performance
    def next_power_of_2(x):
        return 1 << (x - 1).bit_length()
    
    # Determine meta-parameters
    acc_type = tl.float32 if a.dtype in [torch.float16, torch.bfloat16, torch.float32] else a.dtype
    out_type = a.dtype
    
    # Use tensor cores for appropriate dtypes
    if a.dtype == torch.float16:
        acc_type = tl.float16
    elif a.dtype == torch.bfloat16:
        acc_type = tl.bfloat16
    
    # Choose whether to use tensor core optimized memory stages
    STAGE_A = 3 if a.stride(0) == 1 and a.stride(1) >= M else 1
    STAGE_B = 3 if b.stride(1) == 1 and b.stride(0) >= K else 1
    
    # Grid and kernel launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    # Launch kernel
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        EVEN_K=K % 64 == 0,
        STAGE_A=STAGE_A,
        STAGE_B=STAGE_B,
        ACC_TYPE=acc_type,
        OUT_TYPE=out_type,
    )
    
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
from typing import Optional, Tuple


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K', 'STAGE_A', 'STAGE_B', 'EVEN_K', 'ACC_TYPE', 'OUT_TYPE',
         'stride_am', 'stride_ak', 'stride_bk', 'stride_bn']
)
@triton.jit
def _matmul_kernel(
    # Pointers to matrices
    A, B, C,
    # Matrix dimensions
    M, N, K,
    # Stride variables
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, SPLIT_K: tl.constexpr,
    EVEN_K: tl.constexpr, STAGE_A: tl.constexpr, STAGE_B: tl.constexpr,
    ACC_TYPE: tl.constexpr, OUT_TYPE: tl.constexpr,
):
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of C it should compute.
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # ----------------------------------------------------------
    # Create pointers for the first blocks of A and B.
    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)
    a_ptrs = A + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)

    # -----------------------------------------------------------
    # Iterate to compute a block of the C matrix.
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    if STAGE_A == 3:
        a_ptrs = tl.make_block_ptr(base=A, shape=(M, K), strides=(stride_am, stride_ak),
                                   offsets=(pid_m * BLOCK_M, 0), block_shape=(BLOCK_M, BLOCK_K),
                                   order=(1, 0))
    if STAGE_B == 3:
        b_ptrs = tl.make_block_ptr(base=B, shape=(K, N), strides=(stride_bk, stride_bn),
                                   offsets=(0, pid_n * BLOCK_N), block_shape=(BLOCK_K, BLOCK_N),
                                   order=(0, 1))

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        if EVEN_K:
            if STAGE_A == 3:
                a = tl.load(a_ptrs, boundary_check=(0, 1))
                a_ptrs = tl.advance(a_ptrs, (0, BLOCK_K))
            else:
                a = tl.load(a_ptrs)
            if STAGE_B == 3:
                b = tl.load(b_ptrs, boundary_check=(0, 1))
                b_ptrs = tl.advance(b_ptrs, (BLOCK_K, 0))
            else:
                b = tl.load(b_ptrs)
        else:
            k_remaining = K - k * BLOCK_K
            if STAGE_A == 3:
                a = tl.load(a_ptrs, boundary_check=(0, 1))
                a_ptrs = tl.advance(a_ptrs, (0, BLOCK_K))
            else:
                a = tl.load(a_ptrs, mask=offs_k[None, :] < k_remaining, other=0.0)
            if STAGE_B == 3:
                b = tl.load(b_ptrs, boundary_check=(0, 1))
                b_ptrs = tl.advance(b_ptrs, (BLOCK_K, 0))
            else:
                b = tl.load(b_ptrs, mask=offs_k[:, None] < k_remaining, other=0.0)
        
        accumulator += tl.dot(a, b, out_dtype=ACC_TYPE)
        
        if STAGE_A != 3:
            a_ptrs += BLOCK_K * stride_ak
        if STAGE_B != 3:
            b_ptrs += BLOCK_K * stride_bk

    # Apply GELU activation
    accumulator = gelu(accumulator)
    
    # -----------------------------------------------------------
    # Write back the block of the output matrix C
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_ptrs = C + stride_cm * offs_cm[:, None] + stride_cn * offs_cn[None, :]
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    tl.store(c_ptrs, accumulator.to(OUT_TYPE), mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # Check dimensions
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    M, K = a.shape
    K, N = b.shape
    
    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    # Determine meta-parameters
    acc_type = tl.float32 if a.dtype in [torch.float16, torch.bfloat16, torch.float32] else a.dtype
    out_type = a.dtype
    
    # Use tensor cores for appropriate dtypes
    if a.dtype == torch.float16:
        acc_type = tl.float16
    elif a.dtype == torch.bfloat16:
        acc_type = tl.bfloat16
    
    # Choose whether to use tensor core optimized memory stages
    STAGE_A = 3 if a.stride(0) == 1 and a.stride(1) >= M else 1
    STAGE_B = 3 if b.stride(1) == 1 and b.stride(0) >= K else 1
    
    # Grid and kernel launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    # Launch kernel
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        EVEN_K=K % 64 == 0,
        STAGE_A=STAGE_A,
        STAGE_B=STAGE_B,
        ACC_TYPE=acc_type,
        OUT_TYPE=out_type,
    )
    
    return c
'''
        return {"code": code}