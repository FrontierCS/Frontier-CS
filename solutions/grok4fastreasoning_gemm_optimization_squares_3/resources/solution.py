import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def _matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_am: tl.int32, stride_ak: tl.int32,
    stride_bk: tl.int32, stride_bn: tl.int32,
    stride_cm: tl.int32, stride_cn: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    num_k_blocks = (K + BLOCK_K - 1) // BLOCK_K
    for k_block in range(0, num_k_blocks):
        start_k = k_block * BLOCK_K
        offs_k = tl.arange(0, BLOCK_K)
        mask_k = (start_k + offs_k) < K
        mask_m = offs_m < M
        mask_n = offs_n < N
        a_offs = (offs_m[:, None] * stride_am) + ((start_k + offs_k)[None, :] * stride_ak)
        a_ptrs = A_PTR + a_offs
        a_mask = mask_m[:, None] & mask_k[None, :]
        a_tile = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b_offs = ((start_k + offs_k)[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)
        b_ptrs = B_PTR + b_offs
        b_mask = mask_k[:, None] & mask_n[None, :]
        b_tile = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a_tile, b_tile)
    acc = gelu(acc)
    c_offs = (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_ptrs = C_PTR + c_offs
    c_mask = mask_m[:, None] & mask_n[None, :]
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0]
    M, K = a.shape
    _, N = b.shape
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    if M == 0 or N == 0 or K == 0:
        return C
    def kernel_wrapper(
        A_PTR, B_PTR, C_PTR, M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
        **metadata
    ):
        BLOCK_M = metadata['BLOCK_M']
        BLOCK_N = metadata['BLOCK_N']
        BLOCK_K = metadata['BLOCK_K']
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        _matmul_kernel[grid](
            A_PTR, B_PTR, C_PTR, M, N, K,
            stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
        )
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
    ]
    kernel_autotune = triton.autotune(
        configs=configs,
        key=['M', 'N', 'K'],
    )(kernel_wrapper)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    kernel_autotune(
        a, b, C, M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return C
"""
        return {"code": code}
