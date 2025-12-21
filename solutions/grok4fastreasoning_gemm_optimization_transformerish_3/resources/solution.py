import torch
import triton
import triton.language as tl
from typing import Optional

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2
    K = K1
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    if K == 0 or M == 0 or N == 0:
        return c
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    configs = [
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8),
    ]
    @triton.autotune(
        configs,
        key=['M', 'N', 'K'],
    )
    @triton.jit
    def kernel(
        A_PTR,
        B_PTR,
        C_PTR,
        M: tl.int32,
        N: tl.int32,
        K: tl.int32,
        stride_am: tl.int32,
        stride_ak: tl.int32,
        stride_bk: tl.int32,
        stride_bn: tl.int32,
        stride_cm: tl.int32,
        stride_cn: tl.int32,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        block_start_m = pid_m * BLOCK_M
        block_start_n = pid_n * BLOCK_N
        offs_m = tl.arange(0, BLOCK_M)
        offs_n = tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k_start in range(0, K, BLOCK_K):
            offs_ak = k_start + offs_k
            a_ptrs = A_PTR + (block_start_m + offs_m)[:, None] * stride_am + offs_ak[None, :] * stride_ak
            a_mask = (block_start_m + offs_m)[:, None] < M & offs_ak[None, :] < K
            a_block = tl.load(a_ptrs, mask=a_mask, other=0.0)
            b_ptrs = B_PTR + offs_ak[:, None] * stride_bk + (block_start_n + offs_n)[None, :] * stride_bn
            b_mask = offs_ak[:, None] < K & (block_start_n + offs_n)[None, :] < N
            b_block = tl.load(b_ptrs, mask=b_mask, other=0.0)
            acc += tl.dot(a_block, b_block)
        c_ptrs = C_PTR + (block_start_m + offs_m)[:, None] * stride_cm + (block_start_n + offs_n)[None, :] * stride_cn
        c_mask = (block_start_m + offs_m)[:, None] < M & (block_start_n + offs_n)[None, :] < N
        c_block = gelu(acc)
        tl.store(c_ptrs, c_block, mask=c_mask)
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))
    kernel[grid](a, b, c, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn)
    return c
"""
        return {"code": code}
