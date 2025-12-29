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
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 8}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 4}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 5, 'num_warps': 8}),
]

@triton.autotune(
    configs=configs,
    key=['M', 'N', 'K', 'stride_am', 'stride_ak', 'stride_bk', 'stride_bn', 'stride_cm', 'stride_cn'],
)
@triton.jit
def kernel(
    A_PTR, B_PTR, C_PTR, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    program_id_m = tl.program_id(0)
    program_id_n = tl.program_id(1)
    starts_m = program_id_m * BLOCK_M
    starts_n = program_id_n * BLOCK_N
    m_i = tl.arange(0, BLOCK_M)
    n_i = tl.arange(0, BLOCK_N)
    mask_m_i = starts_m + m_i < M
    mask_n_i = starts_n + n_i < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    lo, hi = 0, K
    while lo < hi:
        offs_k_start = lo
        k_i = tl.arange(0, BLOCK_K)
        offs_k = offs_k_start + k_i
        mask_k = offs_k < K
        # A
        mask_a = mask_m_i[:, None] & mask_k[None, :]
        a_ptrs = A_PTR + ((starts_m + m_i)[:, None] * stride_am + offs_k[None, :] * stride_ak)
        a = tl.load(a_ptrs, mask=mask_a, other=0.0).to(tl.float32)
        # B
        mask_b = mask_k[:, None] & mask_n_i[None, :]
        b_ptrs = B_PTR + (offs_k[:, None] * stride_bk + (starts_n + n_i)[None, :] * stride_bn)
        b = tl.load(b_ptrs, mask=mask_b, other=0.0).to(tl.float32)
        # dot
        acc += tl.dot(a, b)
        lo += BLOCK_K
    # gelu
    acc = gelu(acc)
    # store
    mask_c = mask_m_i[:, None] & mask_n_i[None, :]
    c_ptrs = C_PTR + ((starts_m + m_i)[:, None] * stride_cm + (starts_n + n_i)[None, :] * stride_cn)
    tl.store(c_ptrs, acc, mask=mask_c)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, Ka = a.shape
    Kb, N = b.shape
    assert Ka == Kb
    K = Ka
    compute_type = torch.float32
    c = torch.empty((M, N), dtype=compute_type, device=a.device)
    a_ptr = a.data_ptr()
    b_ptr = b.data_ptr()
    c_ptr = c.data_ptr()
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    BLOCK_M = 128
    BLOCK_N = 128
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    kernel[grid](
        a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return c.to(a.dtype)
"""
        return {"code": code}