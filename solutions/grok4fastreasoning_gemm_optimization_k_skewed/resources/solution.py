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
    A_PTR, B_PTR, C_PTR,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M : tl.constexpr,
    BLOCK_N : tl.constexpr,
    BLOCK_K : tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for ko in range(0, K, BLOCK_K):
        offs_k = tl.arange(0, BLOCK_K)
        mask_a = (offs_m[:, None] < M) & (ko + offs_k[None, :] < K)
        a = tl.load(A_PTR + (offs_m[:, None] * stride_am + (ko + offs_k)[None, :] * stride_ak), mask=mask_a, other=0.0)
        mask_b = (ko + offs_k[:, None] < K) & (offs_n[None, :] < N)
        b = tl.load(B_PTR + ((ko + offs_k)[:, None] * stride_bk + offs_n[None, :] * stride_bn), mask=mask_b, other=0.0)
        acc += tl.dot(a, b)
    c = gelu(acc)
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(C_PTR + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn), c, mask=mask_c)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    m, k = a.shape
    assert k == b.shape[0]
    n = b.shape[1]
    c = torch.empty((m, n), dtype=a.dtype, device=a.device)
    es = a.element_size()
    stride_am = a.stride(0) * es
    stride_ak = a.stride(1) * es
    stride_bk = b.stride(0) * es
    stride_bn = b.stride(1) * es
    stride_cm = c.stride(0) * es
    stride_cn = c.stride(1) * es
    if m <= 256:
        BLOCK_M = 64
    else:
        BLOCK_M = 128
    if n <= 256:
        BLOCK_N = 64
    else:
        BLOCK_N = 128
    if k <= 64:
        BLOCK_K = 32
    elif k <= 256:
        BLOCK_K = 64
    else:
        BLOCK_K = 128
    grid = (triton.cdiv(m, BLOCK_M), triton.cdiv(n, BLOCK_N))
    matmul_kernel[grid](
        a.data_ptr(),
        b.data_ptr(),
        c.data_ptr(),
        m,
        n,
        k,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    return c
"""
        return {"code": code}
