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

def triton_cdiv(x, y):
    return (x + y - 1) // y

BLOCK_M = 128
BLOCK_N = 128
BLOCK_K = 64
NUM_STAGES = 4
NUM_WARPS = 8

@triton.jit
def matmul_kernel(
    A_PTR,
    B_PTR,
    C_PTR,
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn
):
    bm = BLOCK_M
    bn = BLOCK_N
    bk = BLOCK_K
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    rm = tl.arange(0, bm)
    rn = tl.arange(0, bn)
    acc = tl.zeros((bm, bn), dtype=tl.float32)
    k = 0
    while k < K:
        offs_k = tl.arange(0, bk)
        offs_am = pid_m * bm + rm[:, None]
        offs_ak = k + offs_k[None, :]
        a_ptrs = A_PTR + offs_am * stride_am + offs_ak * stride_ak
        a_mask = (offs_am < M)[:, None] & (offs_ak < K)[None, :]
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        offs_bk = k + offs_k[:, None]
        offs_bn = pid_n * bn + rn[None, :]
        b_ptrs = B_PTR + offs_bk * stride_bk + offs_bn * stride_bn
        b_mask = (offs_bk < K)[:, None] & (offs_bn < N)[None, :]
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
        k += bk
    acc = gelu(acc)
    offs_cm = pid_m * bm + rm[:, None]
    offs_cn = pid_n * bn + rn[None, :]
    c_mask = (offs_cm < M)[:, None] & (offs_cn < N)[None, :]
    c_ptrs = C_PTR + offs_cm * stride_cm + offs_cn * stride_cn
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2
    K = K1
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    grid = (triton_cdiv(M, BLOCK_M), triton_cdiv(N, BLOCK_N))
    matmul_kernel[grid, NUM_STAGES, NUM_WARPS](
        a, b, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn
    )
    return c
"""
        return {"code": code}