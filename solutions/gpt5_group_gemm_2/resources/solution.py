import torch
import triton
import triton.language as tl
from typing import Optional, Dict
from pathlib import Path


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 32, "BLOCK_K": 32}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 64}, num_warps=2, num_stages=2),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    Batches, M, N, K,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    pid_b = tl.program_id(axis=2)

    m0 = pid_m * BLOCK_M
    n0 = pid_n * BLOCK_N

    offs_m = m0 + tl.arange(0, BLOCK_M)
    offs_n = n0 + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb
    C_batch_ptr = C_ptr + pid_b * stride_cb

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def _grid(meta, Batches, M, N, K):
    return (
        triton.cdiv(M, meta["BLOCK_M"]),
        triton.cdiv(N, meta["BLOCK_N"]),
        Batches,
    )


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError("A and B must be 3D tensors with shapes (B, M, K) and (B, K, N) respectively.")
    if A.shape[0] != B.shape[0]:
        raise ValueError("Batch dimensions must match: A.shape[0] != B.shape[0]")
    if A.shape[2] != B.shape[1]:
        raise ValueError("Inner dimensions must match: A.shape[2] != B.shape[1]")
    if A.device.type != "cuda" or B.device.type != "cuda":
        # Fallback for CPU tensors
        out = torch.bmm(A.to(torch.float16), B.to(torch.float16)).to(torch.float16)
        return out

    Batches = A.shape[0]
    M = A.shape[1]
    K = A.shape[2]
    N = B.shape[2]

    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

    _bmm_kernel[_grid](
        A, B, C,
        Batches, M, N, K,
        stride_ab, stride_am, stride_ak,
        stride_bb, stride_bk, stride_bn,
        stride_cb, stride_cm, stride_cn,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
