import os
import math
import torch
import triton
import triton.language as tl

_NEG_INF = float("-inf")
_BUFFER_CACHE = {}


@triton.jit
def _partial_stats_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    T_ptr,
    Mblk_ptr,
    Sblk_ptr,
    Tlogit_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm,
    stride_xk,
    stride_wk,
    stride_wn,
    stride_mblk_m,
    stride_sblk_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    EVEN_K: tl.constexpr,
    EVEN_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    m_mask = offs_m < M
    if EVEN_N:
        n_mask = tl.full((BLOCK_N,), True, tl.int1)
    else:
        n_mask = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    if EVEN_K:
        for k0 in tl.static_range(0, K, BLOCK_K):
            offs_k = k0 + tl.arange(0, BLOCK_K)
            x = tl.load(
                X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
                mask=m_mask[:, None],
                other=0.0,
            ).to(tl.float16)
            w = tl.load(
                W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
                mask=n_mask[None, :],
                other=0.0,
            ).to(tl.float16)
            acc += tl.dot(x, w)
    else:
        for k0 in tl.static_range(0, K, BLOCK_K):
            offs_k = k0 + tl.arange(0, BLOCK_K)
            k_mask = offs_k < K
            x = tl.load(
                X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
                mask=m_mask[:, None] & k_mask[None, :],
                other=0.0,
            ).to(tl.float16)
            w = tl.load(
                W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
                mask=k_mask[:, None] & n_mask[None, :],
                other=0.0,
            ).to(tl.float16)
            acc += tl.dot(x, w)

    b = tl.load(B_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
    logits = acc + b[None, :]

    if not EVEN_N:
        logits = tl.where(n_mask[None, :], logits, _NEG_INF)

    targets = tl.load(T_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)
    local = targets - pid_n * BLOCK_N
    inb = (local >= 0) & (local < BLOCK_N) & m_mask
    match = inb[:, None] & (tl.arange(0, BLOCK_N)[None, :] == local[:, None])
    sel = tl.where(match, logits, _NEG_INF)
    tlogit = tl.max(sel, axis=1)
    tl.store(Tlogit_ptr + offs_m, tlogit, mask=inb)

    blk_max = tl.max(logits, axis=1)
    blk_sum = tl.sum(tl.exp(logits - blk_max[:, None]), axis=1)

    tl.store(Mblk_ptr + offs_m * stride_mblk_m + pid_n, blk_max, mask=m_mask)
    tl.store(Sblk_ptr + offs_m * stride_sblk_m + pid_n, blk_sum, mask=m_mask)


@triton.jit
def _final_reduce_kernel(
    Mblk_ptr,
    Sblk_ptr,
    Tlogit_ptr,
    Out_ptr,
    M: tl.constexpr,
    N_BLOCKS: tl.constexpr,
    stride_mblk_m,
    stride_sblk_m,
    BLOCK_R: tl.constexpr,
):
    pid = tl.program_id(0)
    rows = pid * BLOCK_R + tl.arange(0, BLOCK_R)
    rmask = rows < M

    offs_b = tl.arange(0, N_BLOCKS)
    m_mat = tl.load(
        Mblk_ptr + rows[:, None] * stride_mblk_m + offs_b[None, :],
        mask=rmask[:, None],
        other=_NEG_INF,
    )
    s_mat = tl.load(
        Sblk_ptr + rows[:, None] * stride_sblk_m + offs_b[None, :],
        mask=rmask[:, None],
        other=0.0,
    )

    row_max = tl.max(m_mat, axis=1)
    sumexp = tl.sum(s_mat * tl.exp(m_mat - row_max[:, None]), axis=1)
    lse = row_max + tl.log(sumexp)

    tlogit = tl.load(Tlogit_ptr + rows, mask=rmask, other=0.0).to(tl.float32)
    loss = lse - tlogit
    tl.store(Out_ptr + rows, loss, mask=rmask)


def _get_intermediate_buffers(device: torch.device, M: int, n_blocks: int):
    key = (device.index, M, n_blocks)
    bufs = _BUFFER_CACHE.get(key, None)
    if bufs is not None:
        mblk, sblk, tlogit = bufs
        if (
            mblk.is_cuda
            and sblk.is_cuda
            and tlogit.is_cuda
            and mblk.device == device
            and sblk.device == device
            and tlogit.device == device
            and mblk.shape == (M, n_blocks)
            and sblk.shape == (M, n_blocks)
            and tlogit.shape == (M,)
            and mblk.dtype == torch.float32
            and sblk.dtype == torch.float32
            and tlogit.dtype == torch.float32
        ):
            return bufs

    mblk = torch.empty((M, n_blocks), device=device, dtype=torch.float32)
    sblk = torch.empty((M, n_blocks), device=device, dtype=torch.float32)
    tlogit = torch.empty((M,), device=device, dtype=torch.float32)
    _BUFFER_CACHE[key] = (mblk, sblk, tlogit)
    return mblk, sblk, tlogit


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not X.is_cuda:
        logits = X @ W + B
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    M, K = X.shape
    Kw, N = W.shape
    assert Kw == K
    assert B.shape == (N,)
    assert targets.shape == (M,)

    BLOCK_M = 16
    BLOCK_N = 256
    BLOCK_K = 64

    even_k = (K % BLOCK_K) == 0
    even_n = (N % BLOCK_N) == 0
    n_blocks = triton.cdiv(N, BLOCK_N)

    mblk, sblk, tlogit = _get_intermediate_buffers(X.device, M, n_blocks)
    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = (triton.cdiv(M, BLOCK_M), n_blocks)
    _partial_stats_kernel[grid](
        X,
        W,
        B,
        targets,
        mblk,
        sblk,
        tlogit,
        M=M,
        N=N,
        K=K,
        stride_xm=X.stride(0),
        stride_xk=X.stride(1),
        stride_wk=W.stride(0),
        stride_wn=W.stride(1),
        stride_mblk_m=mblk.stride(0),
        stride_sblk_m=sblk.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        EVEN_K=even_k,
        EVEN_N=even_n,
        num_warps=8,
        num_stages=4,
    )

    BLOCK_R = 128
    grid2 = (triton.cdiv(M, BLOCK_R),)
    _final_reduce_kernel[grid2](
        mblk,
        sblk,
        tlogit,
        out,
        M=M,
        N_BLOCKS=n_blocks,
        stride_mblk_m=mblk.stride(0),
        stride_sblk_m=sblk.stride(0),
        BLOCK_R=BLOCK_R,
        num_warps=4,
        num_stages=2,
    )
    return out


_FALLBACK_CODE = None
try:
    _THIS_FILE = os.path.abspath(__file__)
    with open(_THIS_FILE, "r", encoding="utf-8") as f:
        _FALLBACK_CODE = f.read()
except Exception:
    _FALLBACK_CODE = None


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if _FALLBACK_CODE is not None:
            return {"code": _FALLBACK_CODE}
        return {"program_path": os.path.abspath(__file__)}
