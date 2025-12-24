import os
from pathlib import Path
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


def _get_autotune_configs():
    cfgs = [
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=8,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
            num_warps=8,
            num_stages=3,
        ),
        triton.Config(
            {"BLOCK_M": 64, "BLOCK_N": 32, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 32, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
        triton.Config(
            {"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32, "GROUP_M": 8},
            num_warps=4,
            num_stages=4,
        ),
    ]
    return cfgs


@triton.autotune(configs=_get_autotune_configs(), key=["M", "N", "K"])
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
    Batches,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid_mn = tl.program_id(axis=0)
    pid_b = tl.program_id(axis=1)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * num_pid_n
    group_id = pid_mn // group_size
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid_mn % group_size
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_batch_ptr = A_ptr + pid_b * stride_ab
    b_batch_ptr = B_ptr + pid_b * stride_bb
    c_batch_ptr = C_ptr + pid_b * stride_cb

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k0 in tl.static_range(0, K, BLOCK_K):
        k_idxs = k0 + offs_k
        a_ptrs = a_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        b_ptrs = b_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (pid_m < num_pid_m) & (pid_b < Batches) & (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (pid_n < num_pid_n) & (pid_b < Batches) & (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float16)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float16)

        acc += tl.dot(a, b)

    c_ptrs = c_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (pid_m < num_pid_m) & (pid_n < num_pid_n) & (pid_b < Batches) & (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError(f"bmm expects 3D tensors; got A.ndim={A.ndim}, B.ndim={B.ndim}")
    if A.shape[0] != B.shape[0] or A.shape[2] != B.shape[1]:
        raise ValueError(f"shape mismatch: A={tuple(A.shape)}, B={tuple(B.shape)}")

    batch, M, K = A.shape
    _, _, N = B.shape

    if batch == 0 or M == 0 or N == 0:
        return torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    if not A.is_cuda or not B.is_cuda:
        return torch.bmm(A, B).to(torch.float16)

    if A.dtype != torch.float16:
        A = A.to(torch.float16)
    if B.dtype != torch.float16:
        B = B.to(torch.float16)

    C = torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]), batch)

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
        batch,
        M=M,
        N=N,
        K=K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
