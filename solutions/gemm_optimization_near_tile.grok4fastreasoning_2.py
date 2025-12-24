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

@triton.jit
def kernel(
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

    block_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    block_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = block_m < M
    mask_n = block_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        a_mask = mask_m[:, None] & (offs_k[None, :] < K)
        b_mask = (offs_k[:, None] < K) & mask_n[None, :]

        a_ptrs = A_PTR + block_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        b_ptrs = B_PTR + offs_k[:, None] * stride_bk + block_n[None, :] * stride_bn

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b, out_dtype=tl.float32)
        lo += BLOCK_K

    c = gelu(acc)
    c_mask = mask_m[:, None] & mask_n[None, :]

    c_ptrs = C_PTR + block_m[:, None] * stride_cm + block_n[None, :] * stride_cn
    tl.store(c_ptrs, c, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K_a = a.shape
    K_b, N = b.shape
    assert K_a == K_b, "Incompatible dimensions"
    K = K_a

    C = torch.empty((M, N), dtype=a.dtype, device=a.device, requires_grad=False)

    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)

    configs = [
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_warps=8, num_stages=5),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_warps=8, num_stages=5),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_warps=8, num_stages=5),
    ]

    key = (M, N, K, stride_am, stride_ak, stride_bk, stride_bn)
    best_config = triton.autotune(
        configs,
        key=key,
        warmup=3,
    )

    BLOCK_M = best_config['BLOCK_M']
    BLOCK_N = best_config['BLOCK_N']
    BLOCK_K = best_config['BLOCK_K']
    num_warps = best_config.get('num_warps', 4)
    num_stages = best_config.get('num_stages', 1)

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    kernel[grid, num_warps=num_warps, num_stages=num_stages](
        a, b, C,
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )

    return C
"""
        return {"code": code}
