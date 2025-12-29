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
def triton_gemm_kernel(
    A_PTR, B_PTR, C_PTR,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pidM = tl.program_id(0)
    pidN = tl.program_id(1)
    block_start_M = pidM * BLOCK_M
    block_start_N = pidN * BLOCK_N
    offs_M = block_start_M + tl.arange(0, BLOCK_M)
    offs_N = block_start_N + tl.arange(0, BLOCK_N)
    offs_K = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_k_cur = start_k + offs_K
        a_offset = offs_M[:, None] * stride_am + offs_k_cur[None, :] * stride_ak
        a_ptrs = A_PTR + a_offset.to(tl.int64)
        a_mask = (offs_M[:, None] < M) & (offs_k_cur[None, :] < K)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b_offset = offs_k_cur[:, None] * stride_bk + offs_N[None, :] * stride_bn
        b_ptrs = B_PTR + b_offset.to(tl.int64)
        b_mask = (offs_k_cur[:, None] < K) & (offs_N[None, :] < N)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
    acc = gelu(acc)
    c_offset = offs_M[:, None] * stride_cm + offs_N[None, :] * stride_cn
    c_ptrs = C_PTR + c_offset.to(tl.int64)
    c_mask = (offs_M[:, None] < M) & (offs_N[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0]
    M, K = a.shape
    N = b.shape[1]
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
    ]
    @triton.autotune(
        configs=configs,
        key=["M", "N", "K", stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn],
    )
    def kernel_wrapper(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn):
        cfg = triton.autotune.current_config
        BLOCK_M_ = cfg['BLOCK_M']
        BLOCK_N_ = cfg['BLOCK_N']
        BLOCK_K_ = cfg['BLOCK_K']
        grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))
        triton_gemm_kernel[grid(cfg)](
            a_ptr, b_ptr, c_ptr,
            M, N, K,
            stride_am, stride_ak,
            stride_bk, stride_bn,
            stride_cm, stride_cn,
            BLOCK_M=BLOCK_M_,
            BLOCK_N=BLOCK_N_,
            BLOCK_K=BLOCK_K_,
        )
    kernel_wrapper(
        a.data_ptr(), b.data_ptr(), C.data_ptr(),
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn
    )
    return C
"""
        return {"code": code}