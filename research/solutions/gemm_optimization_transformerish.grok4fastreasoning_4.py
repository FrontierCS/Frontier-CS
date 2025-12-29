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
def gelu_matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    M : tl.int32, N : tl.int32, K : tl.int32,
    stride_am : tl.int32, stride_ak : tl.int32,
    stride_bk : tl.int32, stride_bn : tl.int32,
    stride_cm : tl.int32, stride_cn : tl.int32,
    BLOCK_M : tl.constexpr,
    BLOCK_N : tl.constexpr,
    BLOCK_K : tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k_start in range(0, K, BLOCK_K):
        offs_k = tl.arange(0, BLOCK_K)
        k_end = tl.minimum(k_start + BLOCK_K, K)
        mask_k = offs_k < (k_end - k_start)
        a_ptrs = A_PTR + (offs_m[:, None] * stride_am + (k_start + offs_k)[None, :] * stride_ak)
        mask_a = (offs_m[:, None] < M) & (mask_k[None, :])
        a = tl.load(a_ptrs, mask=mask_a, other=0.0, num_stages=4, dtype=tl.float32)
        b_ptrs = B_PTR + ((k_start + offs_k)[:, None] * stride_bk + offs_n[None, :] * stride_bn)
        mask_b = (mask_k[:, None]) & (offs_n[None, :] < N)
        b = tl.load(b_ptrs, mask=mask_b, other=0.0, num_stages=4, dtype=tl.float32)
        acc += tl.dot(a, b)
    acc = gelu(acc)
    c_ptrs = C_PTR + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=mask_c)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    K_b, N = b.shape
    assert K_b == K
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    gelu_matmul_kernel[grid](
        a, b, C,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    return C
"""
        return {"code": code}