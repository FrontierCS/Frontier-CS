class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    block_k = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_am = pid_m * BLOCK_M + block_m
        offs_bn = pid_n * BLOCK_N + block_n
        a_ptrs = A_PTR + offs_am[:, None] * stride_am + (start_k + block_k)[None, :] * stride_ak
        a_mask = (offs_am[:, None] < M) & ((start_k + block_k)[None, :] < K)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b_ptrs = B_PTR + (start_k + block_k)[:, None] * stride_bk + offs_bn[None, :] * stride_bn
        b_mask = ((start_k + block_k)[:, None] < K) & (offs_bn[None, :] < N)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
    acc = gelu(acc)
    c_ptrs = C_PTR + offs_am[:, None] * stride_cm + offs_bn[None, :] * stride_cn
    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    Kb, N = b.shape
    assert Kb == K
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=2),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_warps=8),
    ]
    @triton.autotune(
        configs=configs,
        key=(M, N, K),
    )
    def launch_kernel(
        A_PTR, B_PTR, C_PTR, M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    ):
        meta = triton.autotune.current_config
        BLOCK_M = meta['BLOCK_M']
        BLOCK_N = meta['BLOCK_N']
        BLOCK_K = meta['BLOCK_K']
        num_warps = meta['num_warps']
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N), 1)
        matmul_kernel[grid, num_warps=num_warps](
            A_PTR, B_PTR, C_PTR,
            M, N, K,
            stride_am, stride_ak,
            stride_bk, stride_bn,
            stride_cm, stride_cn,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_K=BLOCK_K,
        )
    launch_kernel(
        a, b, C, M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return C
"""
        return {"code": code}
