import os
from pathlib import Path
from typing import Optional, Dict

import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


def _check_bmm_args(A: torch.Tensor, B: torch.Tensor):
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError(f"A and B must be 3D tensors, got A.ndim={A.ndim}, B.ndim={B.ndim}")
    if A.shape[0] != B.shape[0]:
        raise ValueError(f"Batch dims must match, got A.shape[0]={A.shape[0]}, B.shape[0]={B.shape[0]}")
    if A.shape[2] != B.shape[1]:
        raise ValueError(f"Inner dims must match, got A.shape[2]={A.shape[2]}, B.shape[1]={B.shape[1]}")
    if not A.is_cuda or not B.is_cuda:
        return
    if A.device != B.device:
        raise ValueError(f"A and B must be on same device, got {A.device} vs {B.device}")


if triton is not None:
    _BMM_CONFIGS = [
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4},
            num_warps=8,
            num_stages=4,
        ),
    ]

    @triton.autotune(configs=_BMM_CONFIGS, key=["M", "N", "K"])
    @triton.jit
    def _bmm_kernel(
        A_ptr,
        B_ptr,
        C_ptr,
        stride_ab,
        stride_am,
        stride_ak,
        stride_bb,
        stride_bk,
        stride_bn,
        stride_cb,
        stride_cm,
        stride_cn,
        M,
        N,
        K,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(axis=0)
        pid_b = tl.program_id(axis=1)

        num_pid_m = tl.cdiv(M, BLOCK_M)
        num_pid_n = tl.cdiv(N, BLOCK_N)

        num_pid_in_group = GROUP_M * num_pid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_M
        pid_in_group = pid - group_id * num_pid_in_group
        pid_m = first_pid_m + (pid_in_group // num_pid_n)
        pid_n = pid_in_group - (pid_in_group // num_pid_n) * num_pid_n

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        A_batch_ptr = A_ptr + pid_b * stride_ab
        B_batch_ptr = B_ptr + pid_b * stride_bb
        C_batch_ptr = C_ptr + pid_b * stride_cb

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
    _check_bmm_args(A, B)

    batch, M, K = A.shape
    _, _, N = B.shape

    if batch == 0 or M == 0 or N == 0:
        return torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    if not A.is_cuda or triton is None:
        # Always return float16 per problem statement
        return torch.bmm(A.to(torch.float16), B.to(torch.float16)).to(torch.float16)

    if A.dtype != torch.float16:
        A = A.to(torch.float16)
    if B.dtype != torch.float16:
        B = B.to(torch.float16)

    C = torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride(0), A.stride(1), A.stride(2)
    stride_bb, stride_bk, stride_bn = B.stride(0), B.stride(1), B.stride(2)
    stride_cb, stride_cm, stride_cn = C.stride(0), C.stride(1), C.stride(2)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]), batch)

    _bmm_kernel[grid](
        A,
        B,
        C,
        stride_ab,
        stride_am,
        stride_ak,
        stride_bb,
        stride_bk,
        stride_bn,
        stride_cb,
        stride_cm,
        stride_cn,
        M,
        N,
        K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}