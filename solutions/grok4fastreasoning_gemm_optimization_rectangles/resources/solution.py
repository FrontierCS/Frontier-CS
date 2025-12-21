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
    A_PTR, B_PTR, C_PTR, M, N, K, 
    stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn, 
    BLOCK_M: tl.constexpr, 
    BLOCK_N: tl.constexpr, 
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        k_offs = k + tl.arange(0, BLOCK_K)
        mask_a = (offs_m[:, None] < M) & (k_offs[None, :] < K)
        a_ptrs = A_PTR + offs_m[:, None] * stride_am + k_offs[None, :] * stride_ak
        a = tl.load(a_ptrs, mask=mask_a, other=0.0)
        mask_b = (k_offs[:, None] < K) & (offs_n[None, :] < N)
        b_ptrs = B_PTR + k_offs[:, None] * stride_bk + offs_n[None, :] * stride_bn
        b = tl.load(b_ptrs, mask=mask_b, other=0.0)
        acc += tl.dot(a, b)
    c = gelu(acc)
    mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    c_ptrs = C_PTR + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptrs, c, mask=mask_c)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    K_b, N = b.shape
    assert K == K_b, f"Expected matching K dimensions: {K} != {K_b}"
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 256, 'BLOCK_K': 64}),
    ]
    @triton.autotune(configs=configs, key=['M', 'N', 'K'])
    def kernel(M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn):
        grid = (
            triton.cdiv(M, BLOCK_M),
            triton.cdiv(N, BLOCK_N)
        )
        matmul_kernel[grid](
            a, b, c,
            M, N, K,
            stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
        )
    kernel(
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return c
"""
        return {"code": code}
