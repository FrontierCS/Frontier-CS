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

configs = [
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=5, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=2),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=4, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 256}, num_stages=5, num_warps=8),
]

@triton.autotune(
    configs=configs,
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
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    block_k = tl.arange(0, BLOCK_K)
    offs_am = pid_m * BLOCK_M + block_m
    offs_bn = pid_n * BLOCK_N + block_n
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_ak = start_k + block_k
        a_ptrs = A_PTR + (offs_am[:, None].to(tl.int64) * stride_am.to(tl.int64) + offs_ak[None, :].to(tl.int64) * stride_ak.to(tl.int64))
        a_mask = (offs_am[:, None] < M) & (offs_ak[None, :] < K)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b_ptrs = B_PTR + (offs_ak[:, None].to(tl.int64) * stride_bk.to(tl.int64) + offs_bn[None, :].to(tl.int64) * stride_bn.to(tl.int64))
        b_mask = (offs_ak[:, None] < K) & (offs_bn[None, :] < N)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
    c = gelu(acc)
    c_ptrs = C_PTR + (offs_am[:, None].to(tl.int64) * stride_cm.to(tl.int64) + offs_bn[None, :].to(tl.int64) * stride_cn.to(tl.int64))
    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M = a.shape[0]
    N = b.shape[1]
    K = a.shape[1]
    c = torch.empty((M, N), dtype=torch.float32, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    matmul_kernel[grid](
        a, b, c,
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
        BLOCK_M=128, BLOCK_N=128, BLOCK_K=64,
    )
    return c
"""
        return {"code": code}
