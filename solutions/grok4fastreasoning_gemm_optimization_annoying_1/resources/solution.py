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
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=5, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
]

@triton.autotune(
    configs=configs,
    key=['M', 'N', 'K'],
)
@triton.jit
def kernel(
    A_PTR, B_PTR, C_PTR,
    M, N, K,
    stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    m_mask = offs_m < M
    n_mask = offs_n < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    a_ptr = tl.make_block_ptr(
        base=A_PTR,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(0, 1),
    )
    b_ptr = tl.make_block_ptr(
        base=B_PTR,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, n_start),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )
    for k in range(0, K, BLOCK_K):
        k_mask = tl.arange(0, BLOCK_K) < (K - k)
        a_block = tl.load_block(a_ptr, mask=(m_mask[:, None], k_mask[None, :]), other=0.0)
        b_block = tl.load_block(b_ptr, mask=(k_mask[:, None], n_mask[None, :]), other=0.0)
        acc += tl.dot(a_block, b_block)
        a_ptr = tl.advance(a_ptr, 0, BLOCK_K)
        b_ptr = tl.advance(b_ptr, BLOCK_K, 0)
    acc = gelu(acc)
    c_ptr = tl.make_block_ptr(
        base=C_PTR,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(m_start, n_start),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(0, 1),
    )
    tl.store_block(c_ptr, acc, mask=(m_mask[:, None], n_mask[None, :]))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    _, N = b.shape
    assert K == b.shape[0]
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
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
    kernel[grid](
        a, b, c,
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
    )
    return c
"""
        return {"code": code}
