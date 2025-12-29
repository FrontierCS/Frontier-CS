import os
from pathlib import Path
from typing import Dict, Optional

import torch
import triton
import triton.language as tl


def _make_configs():
    cfgs = []
    # Optimized for common 64x64x64, plus some fallbacks for other sizes
    for bm, bn, bk, warps, stages in [
        (64, 64, 32, 8, 4),
        (64, 64, 64, 8, 3),
        (64, 64, 32, 4, 4),
        (64, 64, 16, 4, 5),
        (32, 64, 32, 4, 4),
        (64, 32, 32, 4, 4),
        (32, 32, 32, 4, 4),
        (128, 64, 32, 8, 3),
    ]:
        cfgs.append(
            triton.Config(
                {"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk},
                num_warps=warps,
                num_stages=stages,
            )
        )
    return cfgs


@triton.autotune(configs=_make_configs(), key=["M", "N", "K"])
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
):
    pid_mn = tl.program_id(0)
    pid_b = tl.program_id(1)

    grid_n = tl.cdiv(N, BLOCK_N)
    pid_m = pid_mn // grid_n
    pid_n = pid_mn - pid_m * grid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb

    tl.multiple_of(offs_k, 8)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float16)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float16)

        acc += tl.dot(a, b)

        k0 += BLOCK_K

    c_ptrs = C_ptr + pid_b * stride_cb + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError(f"A and B must be 3D tensors; got A.ndim={A.ndim}, B.ndim={B.ndim}")
    if A.shape[0] != B.shape[0]:
        raise ValueError(f"Batch sizes must match; got {A.shape[0]} and {B.shape[0]}")
    if A.shape[2] != B.shape[1]:
        raise ValueError(f"Inner dimensions must match; got A.shape[2]={A.shape[2]} and B.shape[1]={B.shape[1]}")
    if not A.is_cuda or not B.is_cuda:
        raise ValueError("A and B must be CUDA tensors")
    if A.device != B.device:
        raise ValueError("A and B must be on the same device")

    batch, M, K = A.shape
    _, _, N = B.shape

    C = torch.empty((batch, M, N), device=A.device, dtype=torch.float16)
    if batch == 0 or M == 0 or N == 0:
        return C
    if K == 0:
        C.zero_()
        return C

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

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