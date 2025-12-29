import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def kernel(
    A_PTR,
    B_PTR,
    C_PTR,
    M: tl.int32,
    N: tl.int32,
    K: tl.int32,
    stride_am: tl.int64,
    stride_ak: tl.int64,
    stride_bk: tl.int64,
    stride_bn: tl.int64,
    stride_cm: tl.int64,
    stride_cn: tl.int64,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    block_k = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    m_mask = pid_m * BLOCK_M + block_m < M
    n_mask = pid_n * BLOCK_N + block_n < N
    lo = 0
    while lo < K:
        k_mask = lo + block_k < K
        offs_am = pid_m * BLOCK_M + block_m
        offs_ak = lo + block_k
        a_ptrs = A_PTR + (offs_am[:, None] * stride_am + offs_ak[None, :] * stride_ak)
        a_mask = m_mask[:, None] & k_mask[None, :]
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        offs_bn = pid_n * BLOCK_N + block_n
        offs_bk = lo + block_k
        b_ptrs = B_PTR + (offs_bk[:, None] * stride_bk + offs_bn[None, :] * stride_bn)
        b_mask = k_mask[:, None] & n_mask[None, :]
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
        lo += BLOCK_K
    acc = gelu(acc)
    offs_cm = pid_m * BLOCK_M + block_m
    offs_cn = pid_n * BLOCK_N + block_n
    c_ptrs = C_PTR + (offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn)
    c_mask = m_mask[:, None] & n_mask[None, :]
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2
    K = K1
    output = torch.empty((M, N), dtype=a.dtype, device=a.device)
    if M == 0 or N == 0 or K == 0:
        return output
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = output.stride(0)
    stride_cn = output.stride(1)
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 128}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}),
    ]
    @triton.autotune(
        configs=configs,
        key=(M, N, K, stride_am, stride_ak, stride_bk, stride_bn),
    )
    def wrapper(
        a_ptr,
        b_ptr,
        c_ptr,
        M,
        N,
        K,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        if BLOCK_K == 128:
            num_stages = 4
            num_warps = 8
        elif BLOCK_K == 64:
            num_stages = 3
            num_warps = 4
        else:
            num_stages = 2
            num_warps = 4
        kernel[grid, num_stages=num_stages, num_warps=num_warps](
            a_ptr,
            b_ptr,
            c_ptr,
            tl.int32(M),
            tl.int32(N),
            tl.int32(K),
            tl.int64(stride_am),
            tl.int64(stride_ak),
            tl.int64(stride_bk),
            tl.int64(stride_bn),
            tl.int64(stride_cm),
            tl.int64(stride_cn),
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_K=BLOCK_K,
        )
    wrapper(
        a.data_ptr(),
        b.data_ptr(),
        output.data_ptr(),
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn,
    )
    return output
"""
        return {"code": code}