import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional


_bmm_configs = [
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4},
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4},
        num_stages=3,
        num_warps=4,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 2},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {"BLOCK_M": 32, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_stages=2,
        num_warps=2,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 32, "BLOCK_K": 32, "GROUP_M": 8},
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
    Batches,
    M,
    N,
    K,
    stride_ab,
    stride_am,
    stride_ak,
    stride_bb,
    stride_bk,
    stride_bn,
    stride_cb,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    batch_id = tl.program_id(1)

    # Compute blocking for M and N with grouping along M
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group

    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch_ptr = A_ptr + batch_id * stride_ab
    B_batch_ptr = B_ptr + batch_id * stride_bb
    C_batch_ptr = C_ptr + batch_id * stride_cb

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        a_ptrs = (
            A_batch_ptr
            + (offs_m[:, None] * stride_am)
            + (k_idxs[None, :] * stride_ak)
        )
        b_ptrs = (
            B_batch_ptr
            + (k_idxs[:, None] * stride_bk)
            + (offs_n[None, :] * stride_bn)
        )

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)

        k0 += BLOCK_K

    c_ptrs = (
        C_batch_ptr
        + (offs_m[:, None] * stride_cm)
        + (offs_n[None, :] * stride_cn)
    )
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError("A and B must be 3D tensors of shapes (B, M, K) and (B, K, N).")

    if A.shape[0] != B.shape[0]:
        raise ValueError("Batch dimensions of A and B must match.")
    if A.shape[2] != B.shape[1]:
        raise ValueError("Inner dimensions K of A and B must match.")

    Batches, M, K = A.shape
    _, _, N = B.shape

    # Handle empty tensors
    if Batches == 0 or M == 0 or N == 0 or K == 0:
        return torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    if (not A.is_cuda) or (not B.is_cuda) or (not torch.cuda.is_available()):
        # Fallback to PyTorch implementation on CPU or if CUDA is unavailable
        out = torch.bmm(A.to(torch.float32), B.to(torch.float32))
        return out.to(torch.float16)

    if A.device != B.device:
        raise ValueError("A and B must be on the same device.")

    device = A.device

    C = torch.empty((Batches, M, N), device=device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

    def grid(meta):
        return (
            triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),
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
        stride_ab,
        stride_am,
        stride_ak,
        stride_bb,
        stride_bk,
        stride_bn,
        stride_cb,
        stride_cm,
        stride_cn,
    )

    return C


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}