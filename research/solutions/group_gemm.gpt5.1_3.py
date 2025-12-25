import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Optional, Dict


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}


_bmm_configs = [
    triton.Config(
        {
            "BLOCK_M": 64,
            "BLOCK_N": 64,
            "BLOCK_K": 32,
            "GROUP_M": 1,
        },
        num_stages=2,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 128,
            "BLOCK_N": 32,
            "BLOCK_K": 32,
            "GROUP_M": 2,
        },
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 32,
            "BLOCK_N": 128,
            "BLOCK_K": 32,
            "GROUP_M": 2,
        },
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {
            "BLOCK_M": 64,
            "BLOCK_N": 128,
            "BLOCK_K": 32,
            "GROUP_M": 2,
        },
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {
            "BLOCK_M": 128,
            "BLOCK_N": 64,
            "BLOCK_K": 32,
            "GROUP_M": 2,
        },
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {
            "BLOCK_M": 32,
            "BLOCK_N": 64,
            "BLOCK_K": 32,
            "GROUP_M": 1,
        },
        num_stages=2,
        num_warps=2,
    ),
]


@triton.autotune(configs=_bmm_configs, key=["M", "N", "K"])
@triton.jit
def _bmm_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    Batch,
    M,
    N,
    K,
    stride_a_batch,
    stride_am,
    stride_ak,
    stride_b_batch,
    stride_bk,
    stride_bn,
    stride_c_batch,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,  # kept for compatibility with configs, not used explicitly
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    pid_b = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch_ptr = A_ptr + pid_b * stride_a_batch
    B_batch_ptr = B_ptr + pid_b * stride_b_batch
    C_batch_ptr = C_ptr + pid_b * stride_c_batch

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)

        k0 += BLOCK_K

    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.

    Args:
        A: Input tensor of shape (B, M, K)
        B: Input tensor of shape (B, K, N)

    Returns:
        Output tensor of shape (B, M, N) in float16
    """
    if not (A.is_cuda and B.is_cuda):
        # Fallback to PyTorch implementation on CPU or non-CUDA tensors
        return torch.bmm(A.to(torch.float16), B.to(torch.float16)).to(torch.float16)

    assert A.dim() == 3 and B.dim() == 3, "A and B must be 3D tensors (B, M, K) and (B, K, N)"
    assert A.size(0) == B.size(0), "Batch dimensions of A and B must match"
    assert A.size(2) == B.size(1), "Inner dimensions K of A and B must match"

    Batches, M, K = A.shape
    _, _, N = B.shape

    # Handle empty tensors without launching a kernel
    if Batches == 0 or M == 0 or N == 0 or K == 0:
        return torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    A_strides = A.stride()
    B_strides = B.stride()

    stride_a_batch, stride_am, stride_ak = A_strides
    stride_b_batch, stride_bk, stride_bn = B_strides

    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)
    stride_c_batch, stride_cm, stride_cn = C.stride()

    grid = (
        triton.cdiv(M, _bmm_configs[0]["BLOCK_M"]),
        triton.cdiv(N, _bmm_configs[0]["BLOCK_N"]),
        Batches,
    )

    _bmm_kernel[grid](
        A,
        B,
        C,
        Batches,
        M,
        N,
        K,
        stride_a_batch,
        stride_am,
        stride_ak,
        stride_b_batch,
        stride_bk,
        stride_bn,
        stride_c_batch,
        stride_cm,
        stride_cn,
    )

    return C
