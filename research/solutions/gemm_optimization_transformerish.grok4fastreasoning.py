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
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}),
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
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = A_PTR + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_PTR + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    m_mask = offs_m[:, None] < M
    n_mask = offs_n[None, :] < N

    k = 0
    while True:
        k_mask = offs_k[None, :] < (K - k)
        a_mask = m_mask & k_mask
        b_mask = (offs_k[:, None] < (K - k)) & n_mask

        a = tl.load(a_ptrs + k * stride_ak, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs + k * stride_bk, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        k += BLOCK_K
        if k >= K:
            break

    acc = gelu(acc)

    c_mask = m_mask & n_mask
    c_ptrs = C_PTR + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2, f"Incompatible dimensions: K1={K1}, K2={K2}"
    K = K1

    output = torch.empty((M, N), device=a.device, dtype=torch.float32)

    def grid(meta):
        BLOCK_M = meta['BLOCK_M']
        BLOCK_N = meta['BLOCK_N']
        return (
            (M + BLOCK_M - 1) // BLOCK_M,
            (N + BLOCK_N - 1) // BLOCK_N,
        )

    matmul_kernel[grid](
        a, b, output,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        output.stride(0), output.stride(1),
    )
    return output
"""
        return {"code": code}
