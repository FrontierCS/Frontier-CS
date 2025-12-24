import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r'''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=2),

        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 64, "GROUP_M": 4}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 4}, num_warps=8, num_stages=3),

        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8, num_stages=4),

        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 16, "GROUP_M": 8}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 4}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 64, "GROUP_M": 4}, num_warps=8, num_stages=3),
    ],
    key=["M", "N", "K"]
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    num_pid_in_group = group_size * num_pid_n

    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size
    pid_m = first_pid_m + (pid % group_size)
    pid_n = (pid % num_pid_in_group) // group_size

    pid_m = tl.minimum(pid_m, num_pid_m - 1)
    pid_n = tl.minimum(pid_n, num_pid_n - 1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = 0
    while k_iter < K:
        k_remaining = K - k_iter
        k_mask = offs_k[None, :] < k_remaining

        a_mask = (offs_m[:, None] < M) & k_mask
        b_mask = k_mask.T & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_iter += BLOCK_K

    acc = gelu(acc)

    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.

    Args:
        a: Tensor of shape (M, K)
        b: Tensor of shape (K, N)
    Returns:
        Tensor of shape (M, N) with GELU activation applied
    """
    if not (a.is_cuda and b.is_cuda):
        # Fallback for CPU tensors or other devices
        return torch.nn.functional.gelu(a @ b)

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D matrices")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible matrix shapes for multiplication")

    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb

    # Use common dtype/promotion
    # Triton kernels support float16, bfloat16, float32
    supported_dtypes = (torch.float16, torch.bfloat16, torch.float32)
    if a.dtype not in supported_dtypes or b.dtype not in supported_dtypes:
        a = a.to(torch.float32)
        b = b.to(torch.float32)
    elif a.dtype != b.dtype:
        # Promote to the wider of the two
        target_dtype = torch.promote_types(a.dtype, b.dtype)
        a = a.to(target_dtype)
        b = b.to(target_dtype)

    out_dtype = a.dtype
    C = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a, b, C,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        C.stride(0), C.stride(1),
    )

    return C
'''
        )
        return {"code": code}
