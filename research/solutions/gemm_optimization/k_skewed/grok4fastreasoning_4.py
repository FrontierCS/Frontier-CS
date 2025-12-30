import torch
import triton
import triton.language as tl

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
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
    ]
    @triton.autotune(
        configs=configs,
        key=['M', 'N', 'K'],
    )
    @triton.jit
    def kernel(
        A_PTR, B_PTR, C_PTR, M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        lo, hi = 0, K
        while lo < hi:
            offs_k = tl.arange(0, BLOCK_K)
            offs_am = rm[:, None]
            offs_ak = lo + offs_k[None, :]
            a_mask = (offs_am < M)[:, None] & (offs_ak < K)[None, :]
            a_ptrs = A_PTR + offs_am * stride_am + offs_ak * stride_ak
            a = tl.load(a_ptrs, mask=a_mask, other=0.0)
            offs_bk = lo + offs_k[:, None]
            offs_bn = rn[None, :]
            b_mask = (offs_bk < K)[:, None] & (offs_bn < N)[None, :]
            b_ptrs = B_PTR + offs_bk * stride_bk + offs_bn * stride_bn
            b = tl.load(b_ptrs, mask=b_mask, other=0.0)
            acc += tl.dot(a, b)
            lo += BLOCK_K
        c = gelu(acc)
        offs_cm = rm[:, None]
        offs_cn = rn[None, :]
        c_mask = (offs_cm < M)[:, None] & (offs_cn < N)[None, :]
        c_ptrs = C_PTR + offs_cm * stride_cm + offs_cn * stride_cn
        tl.store(c_ptrs, c, mask=c_mask)
    grid = lambda meta: (
        triton.cdiv(M, meta['BLOCK_M']),
        triton.cdiv(N, meta['BLOCK_N']),
    )
    kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c
"""
        return {"code": code}