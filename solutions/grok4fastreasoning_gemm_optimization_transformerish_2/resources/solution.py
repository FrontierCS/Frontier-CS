class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
import math

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def matmul_kernel(
    A_PTR,
    B_PTR,
    C_PTR,
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

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for start_k in range(0, K, BLOCK_K):
        offs_k_start = start_k + offs_k

        # Load A block
        a_ptr = A_PTR + (offs_m[:, None] * stride_am + offs_k_start[None, :] * stride_ak)
        a_mask = (offs_m[:, None] < M) & (offs_k_start[None, :] < K)
        a = tl.load(a_ptr, mask=a_mask, other=0.0)

        # Load B block
        b_ptr = B_PTR + (offs_k_start[:, None] * stride_bk + offs_n[None, :] * stride_bn)
        b_mask = (offs_k_start[:, None] < K) & (offs_n[None, :] < N)
        b = tl.load(b_ptr, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

    c = gelu(acc)

    # Store C block
    c_ptr = C_PTR + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptr, c, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    _, N = b.shape  # Ensure K matches
    assert a.shape[1] == b.shape[0], "Dimension mismatch"

    device = a.device
    dtype = torch.float32  # Use fp32 for precision with GELU

    c = torch.empty((M, N), dtype=dtype, device=device)

    if a.dtype != dtype:
        a_ref = a.to(dtype)
    else:
        a_ref = a
    if b.dtype != dtype:
        b_ref = b.to(dtype)
    else:
        b_ref = b

    stride_am = a_ref.stride(0)
    stride_ak = a_ref.stride(1)
    stride_bk = b_ref.stride(0)
    stride_bn = b_ref.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)

    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    matmul_kernel[grid](
        a_ref,
        b_ref,
        c,
        M,
        N,
        K,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
    )

    if a.dtype != dtype:
        c = c.to(a.dtype)
    return c
'''
        return {"code": code}
