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
        triton.Config(num_warps=4, num_stages=2),
        triton.Config(num_warps=8, num_stages=2),
        triton.Config(num_warps=4, num_stages=3),
        triton.Config(num_warps=8, num_stages=3),
        triton.Config(num_warps=4, num_stages=4),
        triton.Config(num_warps=8, num_stages=4),
        triton.Config(num_warps=4, num_stages=5),
        triton.Config(num_warps=8, num_stages=5),
        triton.Config(num_warps=8, num_stages=6),
    ],
    key=['M', 'N', 'K', 'stride_am', 'stride_ak', 'stride_bk', 'stride_bn'],
)
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
):
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    k = 0
    while k < K:
        rk = k + tl.arange(0, BLOCK_K)
        a_ptrs = a_ptr + rm[:, None] * stride_am + rk[None, :] * stride_ak
        b_ptrs = b_ptr + rk[:, None] * stride_bk + rn[None, :] * stride_bn
        a_mask = (rm[:, None] < M) & (rk[None, :] < K)
        b_mask = (rk[:, None] < K) & (rn[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
        k += BLOCK_K
    c = gelu(acc)
    c_ptrs = c_ptr + rm[:, None] * stride_cm + rn[None, :] * stride_cn
    c_mask = (rm[:, None] < M) & (rn[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D tensors"
    M, Ka = a.shape
    Kb, N = b.shape
    assert Ka == Kb, f"Incompatible K dimensions: {Ka} != {Kb}"
    K = Ka
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    grid = (triton.cdiv(M, 128), triton.cdiv(N, 128))
    matmul_kernel[grid](
        a.data_ptr(), b.data_ptr(), c.data_ptr(),
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return c
"""
        return {"code": code}
