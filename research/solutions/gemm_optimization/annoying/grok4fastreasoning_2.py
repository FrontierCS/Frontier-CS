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
import math

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M: tl.int32,
    N: tl.int32,
    K: tl.int32,
    stride_am: tl.int32,
    stride_ak: tl.int32,
    stride_bk: tl.int32,
    stride_bn: tl.int32,
    stride_cm: tl.int32,
    stride_cn: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    m_offsets = m_offsets[:, None]
    n_offsets = n_offsets[None, :]

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for start_k in range(0, K, BLOCK_K):
        k_offsets = start_k + tl.arange(0, BLOCK_K)
        a_offsets = m_offsets * stride_am + k_offsets[None, :] * stride_ak
        b_offsets = k_offsets[:, None] * stride_bk + n_offsets * stride_bn

        m_mask = m_offsets < M
        n_mask = n_offsets < N
        k_mask = k_offsets < K
        a_mask = m_mask & k_mask[None, :]
        b_mask = k_mask[:, None] & n_mask

        a_ptrs = a_ptr + a_offsets
        b_ptrs = b_ptr + b_offsets
        a = tl.load(a_ptrs, mask=a_mask, other=0.0, dtype=tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0, dtype=tl.float32)
        acc += tl.dot(a, b)

    acc = gelu(acc)

    c_offsets = m_offsets * stride_cm + n_offsets * stride_cn
    c_mask = m_mask & n_mask[None, :]
    c_ptrs = c_ptr + c_offsets
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    _, N = b.shape
    assert K == b.shape[0]
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    if a.dtype != torch.float32:
        a = a.to(torch.float32)
        b = b.to(torch.float32)
        C = C.to(torch.float32)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    a_ptr = a.data_ptr()
    b_ptr = b.data_ptr()
    c_ptr = C.data_ptr()

    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=1, num_warps=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64}, num_stages=2, num_warps=4),
    ]

    @triton.autotune(configs=configs, key=['M', 'N', 'K'])
    def kernel(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
               BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
        matmul_kernel(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak,
                      stride_bk, stride_bn, stride_cm, stride_cn,
                      BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K)

    def grid(meta):
        BLOCK_M = meta['BLOCK_M']
        BLOCK_N = meta['BLOCK_N']
        return (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    kernel[grid](a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak,
                 stride_bk, stride_bn, stride_cm, stride_cn)
    if C.dtype != torch.float32:
        C = C.to(a.dtype)
    return C
"""
        return {"code": code}