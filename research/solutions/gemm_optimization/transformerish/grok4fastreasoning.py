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
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    def grid(meta):
        return (
            triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),
        )

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64}, num_stages=4, num_warps=8),
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64}, num_stages=3, num_warps=4),
            triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64}, num_stages=3, num_warps=4),
            triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 64}, num_stages=2, num_warps=8),
            triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 64}, num_stages=2, num_warps=8),
            triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 128}, num_stages=3, num_warps=4),
        ],
        key=["M", "N", "K"],
    )
    @triton.jit
    def kernel(
        A_PTR,
        B_PTR,
        C_PTR,
        M,
        N,
        K,
        stride_am: tl.constexpr,
        stride_ak: tl.constexpr,
        stride_bk: tl.constexpr,
        stride_bn: tl.constexpr,
        stride_cm: tl.constexpr,
        stride_cn: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        pid = tl.program_id(0)
        num_cta_n = tl.cdiv(N, BLOCK_N)
        pid_m = pid // num_cta_n
        pid_n = pid % num_cta_n
        rm = tl.arange(0, BLOCK_M)
        rn = tl.arange(0, BLOCK_N)
        block_m = pid_m * BLOCK_M + rm
        block_n = pid_n * BLOCK_N + rn
        m_mask = block_m < M
        n_mask = block_n < N
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        rk = tl.arange(0, BLOCK_K)
        for blk in range(tl.cdiv(K, BLOCK_K)):
            offs_k = blk * BLOCK_K + rk
            k_mask = offs_k < K
            a_ptrs = A_PTR + (block_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
            b_ptrs = B_PTR + (offs_k[:, None] * stride_bk + block_n[None, :] * stride_bn)
            a = tl.load(a_ptrs, mask=(m_mask[:, None] & k_mask[None, :]), other=0.0)
            b = tl.load(b_ptrs, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            acc += tl.dot(a, b)
        c = gelu(acc)
        c_ptrs = C_PTR + (block_m[:, None] * stride_cm + block_n[None, :] * stride_cn)
        tl.store(c_ptrs, c, mask=(m_mask[:, None] & n_mask[None, :]))

    kernel[grid](a, b, c, M, N, K, *a.strides, *b.strides, *c.strides)
    return c
"""
        return {"code": code}