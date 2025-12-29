import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=3, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=3, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=3, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=2, num_warps=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=4, num_warps=8),
    ],
    key=[
        "M",
        "N",
        "K",
        "a_stride_am",
        "a_stride_ak",
        "b_stride_bk",
        "b_stride_bn",
        "c_stride_cm",
        "c_stride_cn",
    ],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M,
    N,
    K,
    a_stride_am,
    a_stride_ak,
    b_stride_bk,
    b_stride_bn,
    c_stride_cm,
    c_stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    # Program ID mapping with grouping along M for L2 locality
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    group_id = pid // (num_pid_n * group_size)
    first_pid_m = group_id * group_size
    group_size_m = tl.minimum(num_pid_m - first_pid_m, group_size)
    pid_in_group = pid % (num_pid_n * group_size_m)
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        rk = k + tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + (rm[:, None] * a_stride_am + rk[None, :] * a_stride_ak)
        b_ptrs = b_ptr + (rk[:, None] * b_stride_bk + rn[None, :] * b_stride_bn)

        a_mask = (rm[:, None] < M) & (rk[None, :] < K)
        b_mask = (rk[:, None] < K) & (rn[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

    # Apply GELU activation
    acc = gelu(acc)

    c_ptrs = c_ptr + (rm[:, None] * c_stride_cm + rn[None, :] * c_stride_cn)
    c_mask = (rm[:, None] < M) & (rn[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    Args:
        a: (M, K)
        b: (K, N)
    Returns:
        (M, N) with GELU activation applied
    """
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D"
    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb, "Incompatible dimensions"

    # Allocate output tensor
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    # Extract strides
    a_stride_am, a_stride_ak = a.stride()
    b_stride_bk, b_stride_bn = b.stride()
    c_stride_cm, c_stride_cn = c.stride()

    # Choose launch grid for 1D grouped mapping
    def grid(meta):
        BM, BN = meta["BLOCK_M"], meta["BLOCK_N"]
        return (triton.cdiv(M, BM) * triton.cdiv(N, BN),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        K,
        a_stride_am,
        a_stride_ak,
        b_stride_bk,
        b_stride_bn,
        c_stride_cm,
        c_stride_cn,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        src = """
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=3, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=3, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=3, num_warps=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_stages=2, num_warps=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 4}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_stages=4, num_warps=8),
    ],
    key=[
        "M",
        "N",
        "K",
        "a_stride_am",
        "a_stride_ak",
        "b_stride_bk",
        "b_stride_bn",
        "c_stride_cm",
        "c_stride_cn",
    ],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M,
    N,
    K,
    a_stride_am,
    a_stride_ak,
    b_stride_bk,
    b_stride_bn,
    c_stride_cm,
    c_stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    group_id = pid // (num_pid_n * group_size)
    first_pid_m = group_id * group_size
    group_size_m = tl.minimum(num_pid_m - first_pid_m, group_size)
    pid_in_group = pid % (num_pid_n * group_size_m)
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        rk = k + tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + (rm[:, None] * a_stride_am + rk[None, :] * a_stride_ak)
        b_ptrs = b_ptr + (rk[:, None] * b_stride_bk + rn[None, :] * b_stride_bn)

        a_mask = (rm[:, None] < M) & (rk[None, :] < K)
        b_mask = (rk[:, None] < K) & (rn[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

    acc = gelu(acc)

    c_ptrs = c_ptr + (rm[:, None] * c_stride_cm + rn[None, :] * c_stride_cn)
    c_mask = (rm[:, None] < M) & (rn[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    assert a.dim() == 2 and b.dim() == 2, "Inputs must be 2D"
    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb, "Incompatible dimensions"

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    a_stride_am, a_stride_ak = a.stride()
    b_stride_bk, b_stride_bn = b.stride()
    c_stride_cm, c_stride_cn = c.stride()

    def grid(meta):
        BM, BN = meta["BLOCK_M"], meta["BLOCK_N"]
        return (triton.cdiv(M, BM) * triton.cdiv(N, BN),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M,
        N,
        K,
        a_stride_am,
        a_stride_ak,
        b_stride_bk,
        b_stride_bn,
        c_stride_cm,
        c_stride_cn,
    )
    return c
"""
        return {"code": src}