import math
import os
from typing import Dict, Tuple, Optional

import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 16, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 16, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 16, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=4, num_stages=3),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _linear_ce_stats_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    T_ptr,
    MAX_ptr,
    SUM_ptr,
    TLOG_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm: tl.constexpr,
    stride_xk: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_wn: tl.constexpr,
    stride_b: tl.constexpr,
    stride_stats_m: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    rows = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    cols = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    row_mask = rows < M
    col_mask = cols < N

    t = tl.load(T_ptr + rows, mask=row_mask, other=0).to(tl.int32)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    tl.multiple_of(stride_xk, 1)
    tl.multiple_of(stride_wn, 1)

    for k0 in range(0, K, BLOCK_K):
        k = k0 + tl.arange(0, BLOCK_K)
        k_mask = k < K

        x_ptrs = X_ptr + rows[:, None] * stride_xm + k[None, :] * stride_xk
        w_ptrs = W_ptr + k[:, None] * stride_wk + cols[None, :] * stride_wn

        x = tl.load(x_ptrs, mask=row_mask[:, None] & k_mask[None, :], other=0.0).to(tl.float16)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & col_mask[None, :], other=0.0).to(tl.float16)

        acc += tl.dot(x, w)

    b = tl.load(B_ptr + cols * stride_b, mask=col_mask, other=0.0).to(tl.float32)
    logits = acc + b[None, :]
    logits = tl.where(col_mask[None, :], logits, -float("inf"))

    tile_max = tl.max(logits, axis=1)
    tile_sum = tl.sum(tl.exp(logits - tile_max[:, None]), axis=1)

    stats_offs = rows * stride_stats_m + pid_n
    tl.store(MAX_ptr + stats_offs, tile_max, mask=row_mask)
    tl.store(SUM_ptr + stats_offs, tile_sum, mask=row_mask)

    tgt_mask = (cols[None, :] == t[:, None]) & col_mask[None, :]
    tgt_logit = tl.sum(tl.where(tgt_mask, logits, 0.0), axis=1)
    has_tgt = tl.sum(tgt_mask, axis=1).to(tl.int32)
    tl.store(TLOG_ptr + rows, tgt_logit, mask=row_mask & (has_tgt != 0))


@triton.jit
def _reduce_stats_to_loss_kernel(
    MAX_ptr,
    SUM_ptr,
    TLOG_ptr,
    OUT_ptr,
    M: tl.constexpr,
    n_blocks: tl.constexpr,
    stride_stats_m: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCKS: tl.constexpr,
):
    pid = tl.program_id(0)
    rows = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    row_mask = rows < M

    running_m = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    running_s = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for b0 in range(0, n_blocks, BLOCKS):
        blocks = b0 + tl.arange(0, BLOCKS)
        block_mask = blocks < n_blocks

        max_ptrs = MAX_ptr + rows[:, None] * stride_stats_m + blocks[None, :]
        sum_ptrs = SUM_ptr + rows[:, None] * stride_stats_m + blocks[None, :]

        m_vals = tl.load(max_ptrs, mask=row_mask[:, None] & block_mask[None, :], other=-float("inf")).to(tl.float32)
        s_vals = tl.load(sum_ptrs, mask=row_mask[:, None] & block_mask[None, :], other=0.0).to(tl.float32)

        m_chunk = tl.max(m_vals, axis=1)
        s_chunk = tl.sum(s_vals * tl.exp(m_vals - m_chunk[:, None]), axis=1)

        new_m = tl.maximum(running_m, m_chunk)
        running_s = running_s * tl.exp(running_m - new_m) + s_chunk * tl.exp(m_chunk - new_m)
        running_m = new_m

    logsumexp = tl.log(running_s) + running_m
    tgt = tl.load(TLOG_ptr + rows, mask=row_mask, other=0.0).to(tl.float32)
    out = logsumexp - tgt
    tl.store(OUT_ptr + rows, out, mask=row_mask)


_BUF_CACHE: Dict[Tuple[int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be float16.")
    if B.dtype != torch.float32:
        raise ValueError("B must be float32.")
    if targets.dtype != torch.int64:
        raise ValueError("targets must be int64.")
    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1 or targets.ndim != 1:
        raise ValueError("Invalid input ranks.")

    M, K = X.shape
    K2, N = W.shape
    if K2 != K:
        raise ValueError("Shape mismatch: X is (M,K) and W is (K,N).")
    if B.shape[0] != N:
        raise ValueError("Shape mismatch: B must be (N,).")
    if targets.shape[0] != M:
        raise ValueError("Shape mismatch: targets must be (M,).")

    if M == 0:
        return torch.empty((0,), device=X.device, dtype=torch.float32)

    device_index = X.device.index if X.device.type == "cuda" else -1

    block_n = 128
    n_blocks = triton.cdiv(N, block_n)

    cache_key = (device_index, M, n_blocks)
    if cache_key in _BUF_CACHE:
        max_buf, sum_buf, tlog_buf = _BUF_CACHE[cache_key]
    else:
        max_buf = torch.empty((M, n_blocks), device=X.device, dtype=torch.float32)
        sum_buf = torch.empty((M, n_blocks), device=X.device, dtype=torch.float32)
        tlog_buf = torch.empty((M,), device=X.device, dtype=torch.float32)
        _BUF_CACHE[cache_key] = (max_buf, sum_buf, tlog_buf)

    tlog_buf.zero_()

    stride_xm, stride_xk = X.stride(0), X.stride(1)
    stride_wk, stride_wn = W.stride(0), W.stride(1)
    stride_b = B.stride(0)
    stride_stats_m = max_buf.stride(0)

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))

    _linear_ce_stats_kernel[grid](
        X,
        W,
        B,
        targets,
        max_buf,
        sum_buf,
        tlog_buf,
        M=M,
        N=N,
        K=K,
        stride_xm=stride_xm,
        stride_xk=stride_xk,
        stride_wk=stride_wk,
        stride_wn=stride_wn,
        stride_b=stride_b,
        stride_stats_m=stride_stats_m,
    )

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    BLOCK_M2 = 128
    BLOCKS = 64
    grid2 = (triton.cdiv(M, BLOCK_M2),)

    _reduce_stats_to_loss_kernel[grid2](
        max_buf,
        sum_buf,
        tlog_buf,
        out,
        M=M,
        n_blocks=n_blocks,
        stride_stats_m=stride_stats_m,
        BLOCK_M=BLOCK_M2,
        BLOCKS=BLOCKS,
        num_warps=4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
