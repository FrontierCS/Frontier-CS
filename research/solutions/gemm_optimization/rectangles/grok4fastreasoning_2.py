import torch

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
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=2, num_warps=8),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=2, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
]

@triton.autotune(configs=configs, key=['M', 'N', 'K'])
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    num_pid_n = tl.cdiv(N, BLOCK_N)
    pid = tl.program_id(0)
    block_m = pid // num_pid_n
    block_n = pid % num_pid_n
    offs_m = block_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = block_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    k = 0
    while k < K:
        offs_k = tl.arange(0, BLOCK_K)
        ak = k + offs_k
        a_ptrs = a_ptr + (offs_m[:, None] * stride_am + ak[None, :] * stride_ak)
        a_mask = (offs_m[:, None] < M) & (ak[None, :] < K)
        A = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b_ptrs = b_ptr + (ak[:, None] * stride_bk + offs_n[None, :] * stride_bn)
        b_mask = (ak[:, None] < K) & (offs_n[None, :] < N)
        B = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(A, B)
        k += BLOCK_K
    c = gelu(acc)
    offs_cm = block_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = block_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_ptrs = c_ptr + (offs_cm[:, None] * stride_cm + offs_cn[None, :] * stride_cn)
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2, f"Incompatible dimensions: K1={K1}, K2={K2}"
    dtype = a.dtype
    device = a.device
    c = torch.empty((M, N), dtype=dtype, device=device)
    if M == 0 or N == 0 or K1 == 0:
        return c
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']), )
    matmul_kernel[grid](
        a, b, c, M, N, K1,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return c
"""
        return {"code": code}