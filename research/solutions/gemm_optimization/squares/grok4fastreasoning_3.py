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
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4, num_warps=8),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=5, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
]

@triton.jit(autotune=configs, key=('M', 'N', 'K'))
def matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_am: tl.int32, stride_ak: tl.int32,
    stride_bk: tl.int32, stride_bn: tl.int32,
    stride_cm: tl.int32, stride_cn: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    m_mask = m_offsets < M
    n_mask = n_offsets < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    offset_k = 0
    while offset_k < K:
        k_offsets = offset_k + tl.arange(0, BLOCK_K)
        k_mask = k_offsets < K

        offs_am = (m_offsets[:, None] * stride_am) + (k_offsets[None, :] * stride_ak)
        a_ptrs = A_PTR + offs_am
        a_mask = (m_mask[:, None]) & (k_mask[None, :])
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)

        offs_bk = (k_offsets[:, None] * stride_bk) + (n_offsets[None, :] * stride_bn)
        b_ptrs = B_PTR + offs_bk
        b_mask = (k_mask[:, None]) & (n_mask[None, :])
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)
        offset_k += BLOCK_K

    acc = gelu(acc)

    offs_cm = (m_offsets[:, None] * stride_cm) + (n_offsets[None, :] * stride_cn)
    c_ptrs = C_PTR + offs_cm
    c_mask = (m_mask[:, None]) & (n_mask[None, :])
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    _, N = b.shape[0], b.shape[1] if len(b.shape) > 1 else b.shape[0]
    c = torch.empty((M, N), device=a.device, dtype=torch.float32)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']), )

    matmul_kernel[grid](
        a, b, c,
        torch.int32(M), torch.int32(N), torch.int32(K),
        torch.int32(stride_am), torch.int32(stride_ak),
        torch.int32(stride_bk), torch.int32(stride_bn),
        torch.int32(stride_cm), torch.int32(stride_cn),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
    )
    return c
"""
        return {"code": code}