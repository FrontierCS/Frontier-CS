import math
from pathlib import Path
from typing import Dict, Optional

import torch
import triton
import triton.language as tl


@triton.jit
def _bmm64_kernel(
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
    BATCH: tl.constexpr,
):
    pid_b = tl.program_id(0)

    offs_m = tl.arange(0, 64)
    offs_n = tl.arange(0, 64)
    offs_k = tl.arange(0, 32)

    A_batch = A_ptr + pid_b * stride_ab
    B_batch = B_ptr + pid_b * stride_bb
    C_batch = C_ptr + pid_b * stride_cb

    acc = tl.zeros((64, 64), dtype=tl.float32)

    k0 = offs_k
    A_ptrs = A_batch + (offs_m[:, None] * stride_am) + (k0[None, :] * stride_ak)
    B_ptrs = B_batch + (k0[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)
    a = tl.load(A_ptrs)
    b = tl.load(B_ptrs)
    acc += tl.dot(a, b)

    k1 = offs_k + 32
    A_ptrs = A_batch + (offs_m[:, None] * stride_am) + (k1[None, :] * stride_ak)
    B_ptrs = B_batch + (k1[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)
    a = tl.load(A_ptrs)
    b = tl.load(B_ptrs)
    acc += tl.dot(a, b)

    C_ptrs = C_batch + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    tl.store(C_ptrs, acc.to(tl.float16))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 32, "BLOCK_K": 32}, num_warps=4, num_stages=4),
    ],
    key=["M", "N", "K"],
)
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
    BATCH,
    M,
    N,
    K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    pid_b = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch = A_ptr + pid_b * stride_ab
    B_batch = B_ptr + pid_b * stride_bb
    C_batch = C_ptr + pid_b * stride_cb

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        A_ptrs = A_batch + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(A_ptrs, mask=a_mask, other=0.0)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)

        k0 += BLOCK_K

    C_ptrs = C_batch + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not isinstance(A, torch.Tensor) or not isinstance(B, torch.Tensor):
        raise TypeError("A and B must be torch.Tensor")
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError("A and B must be 3D tensors: A (B,M,K), B (B,K,N)")
    if A.shape[0] != B.shape[0] or A.shape[2] != B.shape[1]:
        raise ValueError("Shape mismatch: A (B,M,K), B (B,K,N) with same batch and matching K")
    if A.device != B.device:
        raise ValueError("A and B must be on the same device")

    batch, M, K = A.shape
    _, _, N = B.shape

    if batch == 0 or M == 0 or N == 0:
        return torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    if not A.is_cuda:
        return torch.bmm(A, B).to(torch.float16)

    if A.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        A = A.to(torch.float16)
    if B.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        B = B.to(torch.float16)

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
            BATCH=batch,
            num_warps=8,
            num_stages=4,
        )
        return C

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]), batch)

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
        M,
        N,
        K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
