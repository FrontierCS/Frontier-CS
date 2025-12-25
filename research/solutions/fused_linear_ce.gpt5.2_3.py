import os
import textwrap


_KERNEL_CODE = textwrap.dedent(
    r"""
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_ce_block_stats_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    T_ptr,
    Max_ptr,
    Sum_ptr,
    TLogit_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm: tl.constexpr,
    stride_xk: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_wn: tl.constexpr,
    stride_maxm: tl.constexpr,
    stride_maxn: tl.constexpr,
    stride_summ: tl.constexpr,
    stride_sumn: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BK: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BM, BN), dtype=tl.float32)

    offs_k = tl.arange(0, BK)
    k_iter = 0
    while k_iter < K:
        k = k_iter + offs_k
        x = tl.load(
            X_ptr + offs_m[:, None] * stride_xm + k[None, :] * stride_xk,
            mask=mask_m[:, None] & (k[None, :] < K),
            other=0.0,
        ).to(tl.float16)
        w = tl.load(
            W_ptr + k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
            mask=(k[:, None] < K) & mask_n[None, :],
            other=0.0,
        ).to(tl.float16)
        acc += tl.dot(x, w)
        k_iter += BK

    b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    logits = tl.cast(acc + b[None, :], tl.float16)
    logits = tl.where(mask_n[None, :], logits, tl.full((1, 1), -float("inf"), tl.float16))
    logits_f32 = tl.cast(logits, tl.float32)

    m_local = tl.max(logits_f32, axis=1)
    s_local = tl.sum(tl.exp(logits_f32 - m_local[:, None]), axis=1)

    tl.store(
        Max_ptr + offs_m * stride_maxm + pid_n * stride_maxn,
        m_local,
        mask=mask_m,
    )
    tl.store(
        Sum_ptr + offs_m * stride_summ + pid_n * stride_sumn,
        s_local,
        mask=mask_m,
    )

    t = tl.load(T_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)
    n_start = pid_n * BN
    within = mask_m & (t >= n_start) & (t < n_start + BN)
    t_idx = t - n_start
    col_ids = tl.arange(0, BN)[None, :]
    t_mask = within[:, None] & (col_ids == t_idx[:, None])
    t_logit = tl.sum(tl.where(t_mask, logits_f32, 0.0), axis=1)
    tl.store(TLogit_ptr + offs_m, t_logit, mask=within)


@triton.jit
def _fused_linear_ce_reduce_kernel(
    Max_ptr,
    Sum_ptr,
    TLogit_ptr,
    Out_ptr,
    M: tl.constexpr,
    nblocks: tl.constexpr,
    stride_maxm: tl.constexpr,
    stride_maxn: tl.constexpr,
    stride_summ: tl.constexpr,
    stride_sumn: tl.constexpr,
    BLOCK_NB: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    offs = tl.arange(0, BLOCK_NB)
    mask = offs < nblocks

    m_blocks = tl.load(
        Max_ptr + row * stride_maxm + offs * stride_maxn,
        mask=mask,
        other=-float("inf"),
    ).to(tl.float32)
    s_blocks = tl.load(
        Sum_ptr + row * stride_summ + offs * stride_sumn,
        mask=mask,
        other=0.0,
    ).to(tl.float32)

    m = tl.max(m_blocks, axis=0)
    sumexp = tl.sum(s_blocks * tl.exp(m_blocks - m), axis=0)

    tlogit = tl.load(TLogit_ptr + row).to(tl.float32)
    loss = tl.log(sumexp) + m - tlogit
    tl.store(Out_ptr + row, loss)


_ce_buf_cache = {}


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16 and B.dtype == torch.float32 and targets.dtype == torch.int64
    assert X.ndim == 2 and W.ndim == 2 and B.ndim == 1 and targets.ndim == 1
    M, K = X.shape
    K2, N = W.shape
    assert K2 == K
    assert B.shape[0] == N
    assert targets.shape[0] == M

    BM = 16
    BN = 64
    BK = 32
    nblocks = (N + BN - 1) // BN

    dev = X.device
    key = (dev.index, M, nblocks)
    bufs = _ce_buf_cache.get(key, None)
    if bufs is None or (bufs[0].device != dev):
        max_buf = torch.empty((M, nblocks), device=dev, dtype=torch.float32)
        sum_buf = torch.empty((M, nblocks), device=dev, dtype=torch.float32)
        tlogit_buf = torch.empty((M,), device=dev, dtype=torch.float32)
        _ce_buf_cache[key] = (max_buf, sum_buf, tlogit_buf)
    else:
        max_buf, sum_buf, tlogit_buf = bufs

    out = torch.empty((M,), device=dev, dtype=torch.float32)

    grid = (triton.cdiv(M, BM), nblocks)

    _fused_linear_ce_block_stats_kernel[grid](
        X,
        W,
        B,
        targets,
        max_buf,
        sum_buf,
        tlogit_buf,
        M=M,
        N=N,
        K=K,
        stride_xm=X.stride(0),
        stride_xk=X.stride(1),
        stride_wk=W.stride(0),
        stride_wn=W.stride(1),
        stride_maxm=max_buf.stride(0),
        stride_maxn=max_buf.stride(1),
        stride_summ=sum_buf.stride(0),
        stride_sumn=sum_buf.stride(1),
        BM=BM,
        BN=BN,
        BK=BK,
        num_warps=8,
        num_stages=4,
    )

    BLOCK_NB = 256
    _fused_linear_ce_reduce_kernel[(M,)](
        max_buf,
        sum_buf,
        tlogit_buf,
        out,
        M=M,
        nblocks=nblocks,
        stride_maxm=max_buf.stride(0),
        stride_maxn=max_buf.stride(1),
        stride_summ=sum_buf.stride(0),
        stride_sumn=sum_buf.stride(1),
        BLOCK_NB=BLOCK_NB,
        num_warps=4,
        num_stages=2,
    )

    return out
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
