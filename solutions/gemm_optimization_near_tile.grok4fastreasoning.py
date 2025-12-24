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
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 128}),
    ],
    key=['M', 'N', 'K', 'stride_am', 'stride_ak', 'stride_bk', 'stride_bn', 'stride_cm', 'stride_cn']
)
@triton.jit
def matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_am: tl.int32, stride_ak: tl.int32,
    stride_bk: tl.int32, stride_bn: tl.int32,
    stride_cm: tl.int32, stride_cn: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m = pid_m * BLOCK_M
    block_n = pid_n * BLOCK_N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_m = block_m + tl.arange(0, BLOCK_M)
        offs_k = start_k + tl.arange(0, BLOCK_K)
        a_ptrs = A_PTR + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        Ablock = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        offs_k_b = start_k + tl.arange(0, BLOCK_K)
        offs_n = block_n + tl.arange(0, BLOCK_N)
        b_ptrs = B_PTR + offs_k_b[:, None] * stride_bk + offs_n[None, :] * stride_bn
        b_mask = (offs_k_b[:, None] < K) & (offs_n[None, :] < N)
        Bblock = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        partial = tl.dot(Ablock, Bblock)
        acc += partial
    acc = gelu(acc)
    offs_m_c = block_m + tl.arange(0, BLOCK_M)
    offs_n_c = block_n + tl.arange(0, BLOCK_N)
    c_ptrs = C_PTR + offs_m_c[:, None] * stride_cm + offs_n_c[None, :] * stride_cn
    c_mask = (offs_m_c[:, None] < M) & (offs_n_c[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K_a = a.shape
    K_b, N = b.shape
    assert K_a == K_b
    K = K_a
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N'])
        )
    matmul_kernel[grid](
        a, b, C,
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return C
"""
        return {"code": code}
