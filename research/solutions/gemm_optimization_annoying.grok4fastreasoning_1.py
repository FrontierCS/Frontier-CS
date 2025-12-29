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

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=1, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    lo = 0
    while lo < K:
        offs_k = tl.arange(0, BLOCK_K) + lo
        mask_a = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        a_ptrs = A_PTR + stride_ak * offs_k[None, :] + stride_am * offs_m[:, None]
        a = tl.load(a_ptrs, mask=mask_a, other=0.0)
        mask_b = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        b_ptrs = B_PTR + stride_bn * offs_n[None, :] + stride_bk * offs_k[:, None]
        b = tl.load(b_ptrs, mask=mask_b, other=0.0)
        acc += tl.dot(a, b)
        lo += BLOCK_K
    c = gelu(acc)
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    c_ptrs = C_PTR + stride_cn * offs_n[None, :] + stride_cm * offs_m[:, None]
    tl.store(c_ptrs, c, mask=mask_c)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2
    K = K1
    c = torch.empty((M, N), dtype=torch.float32, device=a.device)
    a_f = a.contiguous().to(torch.float32)
    b_f = b.contiguous().to(torch.float32)
    size = torch.float32().element_size()
    stride_am = a_f.stride(0) * size
    stride_ak = a_f.stride(1) * size
    stride_bk = b_f.stride(0) * size
    stride_bn = b_f.stride(1) * size
    stride_cm = c.stride(0) * size
    stride_cn = c.stride(1) * size
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    matmul_kernel[grid](
        a_f, b_f, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
    )
    return c
"""
        return {"code": code}