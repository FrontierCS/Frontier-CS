class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import time

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def get_kernel(BLOCK_M, BLOCK_N, BLOCK_K, num_stages, num_warps):
    @triton.jit(num_stages=num_stages, num_warps=num_warps)
    def kernel(A_PTR, B_PTR, C_PTR, M, N, K,
               stride_am: tl.constexpr, stride_ak: tl.constexpr,
               stride_bk: tl.constexpr, stride_bn: tl.constexpr,
               stride_cm: tl.constexpr, stride_cn: tl.constexpr,
               BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for start_k in range(0, K, BLOCK_K):
            offs_k = start_k + tl.arange(0, BLOCK_K)
            a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
            a_ptrs = A_PTR + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
            a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
            b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
            b_ptrs = B_PTR + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)
            b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
            acc += tl.dot(a, b)
        c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        c_ptrs = C_PTR + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
        tl.store(c_ptrs, gelu(acc), mask=c_mask)
    return kernel

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    assert b.shape[0] == K
    N = b.shape[1]
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    configs = [
        dict(BLOCK_M=128, BLOCK_N=128, BLOCK_K=64, num_stages=4, num_warps=8),
        dict(BLOCK_M=64, BLOCK_N=256, BLOCK_K=64, num_stages=3, num_warps=8),
        dict(BLOCK_M=256, BLOCK_N=64, BLOCK_K=64, num_stages=5, num_warps=4),
        dict(BLOCK_M=128, BLOCK_N=256, BLOCK_K=128, num_stages=2, num_warps=8),
        dict(BLOCK_M=64, BLOCK_N=128, BLOCK_K=128, num_stages=4, num_warps=4),
    ]
    a_ptr = a.data_ptr()
    b_ptr = b.data_ptr()
    c_ptr = C.data_ptr()
    args = (a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn)
    best_time = float('inf')
    best_kernel = None
    best_grid = None
    best_params = None
    for cfg in configs:
        kernel = get_kernel(**cfg)
        BM = cfg['BLOCK_M']
        BN = cfg['BLOCK_N']
        BK = cfg['BLOCK_K']
        grid = (triton.cdiv(M, BM), triton.cdiv(N, BN))
        # warmup
        for _ in range(3):
            kernel[grid](*args, BLOCK_M=BM, BLOCK_N=BN, BLOCK_K=BK)
            torch.cuda.synchronize()
        # benchmark
        times = []
        for _ in range(15):
            torch.cuda.synchronize()
            t0 = time.time()
            kernel[grid](*args, BLOCK_M=BM, BLOCK_N=BN, BLOCK_K=BK)
            torch.cuda.synchronize()
            t1 = time.time()
            times.append(t1 - t0)
        mean_time = sum(times) / len(times)
        if mean_time < best_time:
            best_time = mean_time
            best_kernel = kernel
            best_grid = grid
            best_params = (BM, BN, BK)
    # final launch
    BM, BN, BK = best_params
    best_kernel[best_grid](*args, BLOCK_M=BM, BLOCK_N=BN, BLOCK_K=BK)
    torch.cuda.synchronize()
    return C
"""
        return {"code": code}
