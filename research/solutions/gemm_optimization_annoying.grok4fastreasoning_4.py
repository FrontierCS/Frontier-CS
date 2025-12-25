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
    _, N = b.shape
    assert K == b.shape[0]
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
    num_stages = 4
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
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
        num_stages: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_m = offs_m < M
        mask_n = offs_n < N
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for start_k in range(0, K, BLOCK_K):
            offs_k = start_k + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            a_ptrs = A_PTR + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
            a_mask = mask_m[:, None] & mask_k[None, :]
            a = tl.load(a_ptrs, mask=a_mask, other=0.0, num_stages=1 if start_k == 0 else num_stages)
            b_ptrs = B_PTR + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)
            b_mask = mask_k[:, None] & mask_n[None, :]
            b = tl.load(b_ptrs, mask=b_mask, other=0.0, num_stages=1 if start_k == 0 else num_stages)
            acc += tl.dot(a, b)
        acc = gelu(acc)
        c_ptrs = C_PTR + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
        c_mask = mask_m[:, None] & mask_n[None, :]
        tl.store(c_ptrs, acc, mask=c_mask)
    kernel[grid](
        a.data_ptr(), b.data_ptr(), C.data_ptr(),
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn
    )
    return C
"""
        return {"code": code}
