import os
from pathlib import Path
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def _bmm64_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    stride_ab: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ak: tl.constexpr,
    stride_bb: tl.constexpr,
    stride_bk: tl.constexpr,
    stride_bn: tl.constexpr,
    stride_cb: tl.constexpr,
    stride_cm: tl.constexpr,
    stride_cn: tl.constexpr,
    BK: tl.constexpr,
):
    pid_b = tl.program_id(axis=0)

    offs_m = tl.arange(0, 64)
    offs_n = tl.arange(0, 64)
    offs_k = tl.arange(0, BK)

    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb
    C_batch_ptr = C_ptr + pid_b * stride_cb

    acc = tl.zeros((64, 64), dtype=tl.float32)

    for k0 in tl.static_range(0, 64, BK):
        k_idxs = k0 + offs_k
        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn)
        a = tl.load(a_ptrs).to(tl.float16)
        b = tl.load(b_ptrs).to(tl.float16)
        acc += tl.dot(a, b)

    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    tl.store(c_ptrs, acc.to(tl.float16))


_AUTOTUNE_CONFIGS = [
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
        num_warps=8,
        num_stages=2,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=8,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32, "GROUP_M": 8},
        num_warps=4,
        num_stages=4,
    ),
]


@triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["M", "N", "K"])
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
    pid_mn = tl.program_id(axis=0)
    pid_b = tl.program_id(axis=1)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    # Grouped ordering to improve L2 hit rate
    num_pid_in_group = GROUP_M * grid_n
    group_id = pid_mn // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid_mn - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group // grid_n)
    pid_n = pid_in_group % grid_n

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

        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float16)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float16)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (isinstance(A, torch.Tensor) and isinstance(B, torch.Tensor)):
        raise TypeError("A and B must be torch.Tensor")
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError("A and B must be 3D tensors with shapes (B, M, K) and (B, K, N)")
    if A.shape[0] != B.shape[0]:
        raise ValueError("Batch sizes must match")
    if A.shape[2] != B.shape[1]:
        raise ValueError("Inner dimensions must match: A.shape[2] == B.shape[1]")

    batch, M, K = A.shape
    _, _, N = B.shape

    if batch == 0 or M == 0 or N == 0:
        return torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    if not (A.is_cuda and B.is_cuda):
        return torch.bmm(A, B).to(torch.float16)

    C = torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

    if M == 64 and N == 64 and K == 64:
        grid = (batch,)
        _bmm64_kernel[grid](
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
            BK=32,
            num_warps=8,
            num_stages=3,
        )
        return C

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]), batch)

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
