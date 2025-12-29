import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Optional, Dict


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 1},
            num_stages=2,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 1},
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 1},
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 1},
            num_stages=2,
            num_warps=2,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 1},
            num_stages=2,
            num_warps=2,
        ),
    ],
    key=["M", "N", "K"],
)
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

    num_pid_m = (M + BLOCK_M - 1) // BLOCK_M
    num_pid_n = (N + BLOCK_N - 1) // BLOCK_N
    blocks_per_batch = num_pid_m * num_pid_n

    batch_id = pid // blocks_per_batch
    pid_in_batch = pid % blocks_per_batch
    pid_m = pid_in_batch // num_pid_n
    pid_n = pid_in_batch % num_pid_n

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

        A_ptrs = A_batch_ptr + (
            offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak
        )
        B_ptrs = B_batch_ptr + (
            k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn
        )

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)

        k0 += BLOCK_K

    C_ptrs = C_batch_ptr + (
        offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    )
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.dim() != 3 or B.dim() != 3:
        raise ValueError("A and B must be 3D tensors of shapes (B, M, K) and (B, K, N)")

    if A.device.type != "cuda" or B.device.type != "cuda":
        raise ValueError("A and B must be CUDA tensors")

    Batches, M, K = A.shape
    B2, K2, N = B.shape

    if B2 != Batches or K2 != K:
        raise ValueError(
            f"Incompatible shapes for bmm: A {A.shape}, B {B.shape}"
        )

    # Handle degenerate cases without launching kernels
    if Batches == 0 or M == 0 or N == 0:
        return torch.empty(
            (Batches, M, N), device=A.device, dtype=torch.float16
        )

    if K == 0:
        return torch.zeros(
            (Batches, M, N), device=A.device, dtype=torch.float16
        )

    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"])
        * triton.cdiv(N, META["BLOCK_N"])
        * Batches,
    )

    _bmm_kernel[grid](
        A,
        B,
        C,
        Batches,
        M,
        N,
        K,
        A.stride(0),
        A.stride(1),
        A.stride(2),
        B.stride(0),
        B.stride(1),
        B.stride(2),
        C.stride(0),
        C.stride(1),
        C.stride(2),
    )

    return C


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}