import typing

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 4}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 4}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 4}, num_stages=5, num_warps=8),
    ],
    key=['M', 'N', 'K', 'a_stride_am', 'a_stride_ak', 'b_stride_bk', 'b_stride_bn'],
)
@triton.jit
def matmul_kernel(
    A, B, C,
    M, N, K,
    a_stride_am, a_stride_ak,
    b_stride_bk, b_stride_bn,
    c_stride_cm, c_stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_id = pid // (GROUP_M * grid_n)
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid % (GROUP_M * grid_n)
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A + (offs_m[:, None] * a_stride_am + offs_k[None, :] * a_stride_ak)
    b_ptrs = B + (offs_k[:, None] * b_stride_bk + offs_n[None, :] * b_stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    m_mask = offs_m < M
    n_mask = offs_n < N

    k_iter = 0
    while k_iter < K:
        k_mask = (k_iter + offs_k) < K
        a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
        b = tl.load(b_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * a_stride_ak
        b_ptrs += BLOCK_K * b_stride_bk
        k_iter += BLOCK_K

    acc = gelu(acc)
    c_ptrs = C + (offs_m[:, None] * c_stride_cm + offs_n[None, :] * c_stride_cn)
    tl.store(c_ptrs, acc, mask=m_mask[:, None] & n_mask[None, :])

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.is_cuda and b.is_cuda, "Input tensors must be CUDA tensors"
    assert a.ndim == 2 and b.ndim == 2, "Input tensors must be 2D"
    assert a.shape[1] == b.shape[0], "Incompatible matrix dimensions"
    assert a.dtype == b.dtype, "Input tensors must have the same dtype"

    M, K = a.shape
    Kb, N = b.shape
    out = torch.empty((M, N), device=a.device, dtype=a.dtype)

    a_stride_am, a_stride_ak = a.stride()
    b_stride_bk, b_stride_bn = b.stride()
    c_stride_cm, c_stride_cn = out.stride()

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

    matmul_kernel[grid](
        a, b, out,
        M, N, K,
        a_stride_am, a_stride_ak,
        b_stride_bk, b_stride_bn,
        c_stride_cm, c_stride_cn
    )
    return out
'''
        return {"code": code}
