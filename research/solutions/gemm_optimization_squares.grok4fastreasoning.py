class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

configs = [
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 64}),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_warps=8),
]

@triton.autotune(configs=configs, key=lambda *args: (args[3], args[4], args[5]))
@triton.jit
def kernel(
    a_ptr, b_ptr, c_ptr,
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
    rm = tl.arange(0, BLOCK_M)
    rn = tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k_start in range(0, K, BLOCK_K):
        rk = tl.arange(0, BLOCK_K)
        offs_m = pid_m * BLOCK_M + rm
        offs_n = pid_n * BLOCK_N + rn
        offs_k = k_start + rk
        a_offsets = offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        a_ptrs = a_ptr + a_offsets
        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        a_tile = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b_offsets = offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn
        b_ptrs = b_ptr + b_offsets
        b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        b_tile = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a_tile, b_tile)
    acc = gelu(acc)
    c_offsets = offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_ptrs = c_ptr + c_offsets
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K_a = a.shape
    K_b, N = b.shape
    assert K_a == K_b
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0) if len(a.shape) == 2 else K_a
    stride_ak = a.stride(1) if len(a.shape) == 2 else 1
    stride_bk = b.stride(0) if len(b.shape) == 2 else N
    stride_bn = b.stride(1) if len(b.shape) == 2 else 1
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)
    K = K_a
    def grid(meta):
        bm = meta['BLOCK_M']
        bn = meta['BLOCK_N']
        return (triton.cdiv(M, bm), triton.cdiv(N, bn))
    kernel[grid](
        a_ptr=a.data_ptr(),
        b_ptr=b.data_ptr(),
        c_ptr=c.data_ptr(),
        M=M,
        N=N,
        K=K,
        stride_am=stride_am,
        stride_ak=stride_ak,
        stride_bk=stride_bk,
        stride_bn=stride_bn,
        stride_cm=stride_cm,
        stride_cn=stride_cn,
    )
    return c"""
        }
