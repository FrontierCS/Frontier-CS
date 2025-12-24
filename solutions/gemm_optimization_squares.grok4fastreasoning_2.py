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
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 256}, num_stages=5, num_warps=4),
    ],
    key=('M', 'N', 'K'),
)
@triton.jit
def kernel(
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
    offs_m = pid_m * BLOCK_M + block_m
    offs_n = pid_n * BLOCK_N + block_n
    m_mask = offs_m < M
    n_mask = offs_n < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    block_k = tl.arange(0, BLOCK_K)
    lo = 0
    while lo < K:
        offs_k = lo + block_k
        k_mask = offs_k < K
        a_offsets = (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
        a_ptrs = A_PTR + a_offsets
        a_mask = m_mask[:, None] & k_mask[None, :]
        A = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b_offsets = (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)
        b_ptrs = B_PTR + b_offsets
        b_mask = k_mask[:, None] & n_mask[None, :]
        B = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(A, B)
        lo += BLOCK_K
    c = gelu(acc)
    c_offsets = (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_ptrs = C_PTR + c_offsets
    c_mask = m_mask[:, None] & n_mask[None, :]
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    N = b.shape[1]
    C = torch.empty((M, N), dtype=torch.float32, device=a.device)
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    kernel[grid](
        a, b, C,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        C.stride(0), C.stride(1),
    )
    return C
"""
        return {"code": code}
