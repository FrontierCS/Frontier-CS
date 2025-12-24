import os
from pathlib import Path
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def _bmm64_tile64_kernel(
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
    BLOCK_K: tl.constexpr,
):
    pid_b = tl.program_id(0)

    A_batch = A_ptr + pid_b * stride_ab
    B_batch = B_ptr + pid_b * stride_bb
    C_batch = C_ptr + pid_b * stride_cb

    offs_m = tl.arange(0, 64)
    offs_n = tl.arange(0, 64)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((64, 64), dtype=tl.float32)

    tl.multiple_of(stride_ak, 1)
    tl.multiple_of(stride_bn, 1)

    for k0 in tl.static_range(0, 64, BLOCK_K):
        k_idxs = k0 + offs_k
        A_ptrs = A_batch + offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak
        B_ptrs = B_batch + k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn
        a = tl.load(A_ptrs)
        b = tl.load(B_ptrs)
        acc += tl.dot(a, b)

    C_ptrs = C_batch + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(C_ptrs, acc.to(tl.float16))


@triton.jit
def _bmm64_tile32_kernel(
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_b = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_n = tl.program_id(2)

    A_batch = A_ptr + pid_b * stride_ab
    B_batch = B_ptr + pid_b * stride_bb
    C_batch = C_ptr + pid_b * stride_cb

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k0 in tl.static_range(0, 64, BLOCK_K):
        k_idxs = k0 + offs_k
        A_ptrs = A_batch + offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak
        B_ptrs = B_batch + k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn
        a = tl.load(A_ptrs)
        b = tl.load(B_ptrs)
        acc += tl.dot(a, b)

    C_ptrs = C_batch + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(C_ptrs, acc.to(tl.float16))


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32}, num_warps=4, num_stages=4),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _bmm_general_kernel(
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
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid0 = tl.program_id(0)
    pid_n = tl.program_id(1)

    grid_m = tl.cdiv(M, BLOCK_M)
    pid_b = pid0 // grid_m
    pid_m = pid0 - pid_b * grid_m

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
        A_ptrs = A_batch + offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak
        B_ptrs = B_batch + k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(A_ptrs, mask=a_mask, other=0.0)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    C_ptrs = C_batch + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (isinstance(A, torch.Tensor) and isinstance(B, torch.Tensor)):
        raise TypeError("A and B must be torch.Tensors")
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError("A and B must be 3D tensors with shapes (B, M, K) and (B, K, N)")
    if A.shape[0] != B.shape[0]:
        raise ValueError("Batch sizes must match")
    if A.shape[2] != B.shape[1]:
        raise ValueError("Inner dimensions must match: A.shape[2] == B.shape[1]")

    if not A.is_cuda or not B.is_cuda:
        return torch.bmm(A, B).to(torch.float16)

    if A.dtype != torch.float16 and A.dtype != torch.bfloat16:
        A = A.to(torch.float16)
    if B.dtype != torch.float16 and B.dtype != torch.bfloat16:
        B = B.to(torch.float16)

    batch, M, K = A.shape
    _, _, N = B.shape
    C = torch.empty((batch, M, N), device=A.device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

    if M == 64 and N == 64 and K == 64:
        if batch <= 96:
            grid = (batch, 2, 2)
            _bmm64_tile32_kernel[grid](
                A,
                B,
                C,
                stride_ab=stride_ab,
                stride_am=stride_am,
                stride_ak=stride_ak,
                stride_bb=stride_bb,
                stride_bk=stride_bk,
                stride_bn=stride_bn,
                stride_cb=stride_cb,
                stride_cm=stride_cm,
                stride_cn=stride_cn,
                BLOCK_M=32,
                BLOCK_N=32,
                BLOCK_K=32,
                num_warps=4,
                num_stages=4,
            )
        else:
            grid = (batch,)
            _bmm64_tile64_kernel[grid](
                A,
                B,
                C,
                stride_ab=stride_ab,
                stride_am=stride_am,
                stride_ak=stride_ak,
                stride_bb=stride_bb,
                stride_bk=stride_bk,
                stride_bn=stride_bn,
                stride_cb=stride_cb,
                stride_cm=stride_cm,
                stride_cn=stride_cn,
                BLOCK_K=32,
                num_warps=8,
                num_stages=4,
            )
        return C

    def grid(meta):
        return (batch * triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))

    _bmm_general_kernel[grid](
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
        M=M,
        N=N,
        K=K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
