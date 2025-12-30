class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    N = b.shape[1]
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 256}, num_warps=8, num_stages=4),
    ]
    @triton.autotune(
        configs=configs,
        key=['M', 'N', 'K'],
    )
    @triton.jit
    def kernel(A_PTR, B_PTR, C_PTR, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
               BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, num_stages: tl.constexpr, num_warps: tl.constexpr):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        block_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        block_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        k = 0
        while k < K:
            k_offs = k + tl.arange(0, BLOCK_K)
            a_ptrs = A_PTR + (block_m[:, None] * stride_am + k_offs[None, :] * stride_ak)
            a_mask = (block_m[:, None] < M) & (k_offs[None, :] < K)
            A = tl.load(a_ptrs, mask=a_mask, other=0.0, num_stages=num_stages).to(tl.float32)
            b_ptrs = B_PTR + (k_offs[:, None] * stride_bk + block_n[None, :] * stride_bn)
            b_mask = (k_offs[:, None] < K) & (block_n[None, :] < N)
            B = tl.load(b_ptrs, mask=b_mask, other=0.0, num_stages=num_stages).to(tl.float32)
            acc += tl.dot(A, B)
            k += BLOCK_K
        c_val = gelu(acc)
        c_ptrs = C_PTR + (block_m[:, None] * stride_cm + block_n[None, :] * stride_cn)
        c_mask = (block_m[:, None] < M) & (block_n[None, :] < N)
        tl.store(c_ptrs, c_val.to(c.dtype), mask=c_mask)
    BLOCK = 128
    grid = (triton.cdiv(M, BLOCK), triton.cdiv(N, BLOCK))
    kernel[grid](a, b, c, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn)
    return c
"""
        return {"code": code}