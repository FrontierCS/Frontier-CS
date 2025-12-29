import torch
import triton
import triton.language as tl
import math

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
def matmul_kernel(
    A_PTR,
    B_PTR,
    C_PTR,
    M: tl.int32,
    N: tl.int32,
    K: tl.int32,
    stride_am_b: tl.int64,
    stride_ak_b: tl.int64,
    stride_bk_b: tl.int64,
    stride_bn_b: tl.int64,
    stride_cm_b: tl.int64,
    stride_cn_b: tl.int64,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    num_col_blocks = tl.cdiv(N, BLOCK_N)
    pid_m = pid // num_col_blocks
    pid_n = pid % num_col_blocks
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        offs_k = tl.arange(0, BLOCK_K)
        mask_k = offs_k < (K - k)
        m_offset = tl.int64(offs_m[:, None]) * stride_am_b + tl.int64(k + offs_k[None, :]) * stride_ak_b
        kn_offset = tl.int64(k + offs_k[:, None]) * stride_bk_b + tl.int64(offs_n[None, :]) * stride_bn_b
        a_ptrs = tl.int64(A_PTR) + m_offset
        b_ptrs = tl.int64(B_PTR) + kn_offset
        a = tl.load(a_ptrs, mask=(mask_m[:, None] & mask_k[None, :]), other=0.0)
        b = tl.load(b_ptrs, mask=(mask_k[:, None] & mask_n[None, :]), other=0.0)
        acc += tl.dot(a, b)
    c_vals = gelu(acc)
    c_offset = tl.int64(offs_m[:, None]) * stride_cm_b + tl.int64(offs_n[None, :]) * stride_cn_b
    c_ptrs = tl.int64(C_PTR) + c_offset
    tl.store(c_ptrs, c_vals, mask=(mask_m[:, None] & mask_n[None, :]))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, Ka = a.shape
    Kb, N = b.shape
    assert Ka == Kb
    K = Ka
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    itemsize = a.element_size()
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    stride_am_b = stride_am * itemsize
    stride_ak_b = stride_ak * itemsize
    stride_bk_b = stride_bk * itemsize
    stride_bn_b = stride_bn * itemsize
    stride_cm_b = stride_cm * itemsize
    stride_cn_b = stride_cn * itemsize
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 512, 'BLOCK_K': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
    ]
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),
        )
    matmul_kernel[configs, grid](
        a.data_ptr(),
        b.data_ptr(),
        c.data_ptr(),
        M,
        N,
        K,
        stride_am_b,
        stride_ak_b,
        stride_bk_b,
        stride_bn_b,
        stride_cm_b,
        stride_cn_b
    )
    return c
"""
        return {"code": code}