import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_autotune_configs = [
    triton.Config(
        {
            "BLOCK_M": 128,
            "BLOCK_N": 128,
            "BLOCK_K": 32,
            "GROUP_M": 8,
        },
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 64,
            "BLOCK_N": 128,
            "BLOCK_K": 32,
            "GROUP_M": 8,
        },
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 128,
            "BLOCK_N": 64,
            "BLOCK_K": 32,
            "GROUP_M": 8,
        },
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 64,
            "BLOCK_N": 64,
            "BLOCK_K": 32,
            "GROUP_M": 8,
        },
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 128,
            "BLOCK_N": 128,
            "BLOCK_K": 64,
            "GROUP_M": 4,
        },
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {
            "BLOCK_M": 64,
            "BLOCK_N": 128,
            "BLOCK_K": 64,
            "GROUP_M": 4,
        },
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {
            "BLOCK_M": 128,
            "BLOCK_N": 64,
            "BLOCK_K": 64,
            "GROUP_M": 4,
        },
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {
            "BLOCK_M": 64,
            "BLOCK_N": 64,
            "BLOCK_K": 16,
            "GROUP_M": 8,
        },
        num_stages=2,
        num_warps=4,
    ),
]


@triton.autotune(configs=_autotune_configs, key=["M", "N", "K", "C_dtype"])
@triton.jit
def _matmul_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    C_dtype: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n

    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + pid_in_group // num_pid_n
    pid_n = pid_in_group % num_pid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        k_offsets = k + offs_k
        k_mask = k_offsets < K

        a_mask = (offs_m[:, None] < M) & k_mask[None, :]
        b_mask = k_mask[:, None] & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    if C_dtype == 0:
        out = acc
    elif C_dtype == 1:
        out = acc.to(tl.float16)
    elif C_dtype == 2:
        out = acc.to(tl.bfloat16)
    else:
        out = acc

    tl.store(c_ptrs, out, mask=c_mask)


def _torch_gelu(x: torch.Tensor) -> torch.Tensor:
    return x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.

    Args:
        a: Tensor of shape (M, K)
        b: Tensor of shape (K, N)

    Returns:
        Tensor of shape (M, N) with GELU activation applied.
    """
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors of shapes (M, K) and (K, N).")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Inner dimensions must match for matrix multiplication.")
    M, K = a.shape
    Kb, N = b.shape

    if M == 0 or N == 0 or K == 0:
        return _torch_gelu(a @ b)

    if not a.is_cuda or not b.is_cuda:
        return _torch_gelu(a @ b)

    if a.dtype != b.dtype:
        b = b.to(a.dtype)

    dtype = a.dtype
    if dtype not in (torch.float16, torch.bfloat16, torch.float32):
        a = a.to(torch.float32)
        b = b.to(torch.float32)
        dtype = torch.float32

    if dtype == torch.float32:
        c_dtype_id = 0
    elif dtype == torch.float16:
        c_dtype_id = 1
    elif dtype == torch.bfloat16:
        c_dtype_id = 2
    else:
        c_dtype_id = 0

    C = torch.empty((M, N), device=a.device, dtype=dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = C.stride()

    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),
    )

    _matmul_kernel[grid](
        a,
        b,
        C,
        M,
        N,
        K,
        stride_am,
        stride_ak,
        stride_bk,
        stride_bn,
        stride_cm,
        stride_cn,
        C_dtype=c_dtype_id,
    )

    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
