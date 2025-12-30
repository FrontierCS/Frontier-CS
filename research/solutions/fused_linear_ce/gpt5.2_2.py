import textwrap

KERNEL_CODE = textwrap.dedent(
    r"""
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634
_LN2 = 0.6931471805599453

@triton.jit
def _ce_partials_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr,
    PM_ptr, PS_ptr, TL_ptr,
    M: tl.constexpr,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_p,
    N: tl.constexpr, K: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    row_start = pid_m * BLOCK_M
    col_start = pid_n * BLOCK_N

    rows = row_start + tl.arange(0, BLOCK_M)
    cols = col_start + tl.arange(0, BLOCK_N)
    row_mask = rows < M
    col_mask = cols < N

    x_blk = tl.make_block_ptr(
        base=X_ptr,
        shape=(M, K),
        strides=(stride_xm, stride_xk),
        offsets=(row_start, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    w_blk = tl.make_block_ptr(
        base=W_ptr,
        shape=(K, N),
        strides=(stride_wk, stride_wn),
        offsets=(0, col_start),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for _ in tl.static_range(0, K, BLOCK_K):
        a = tl.load(x_blk, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
        b = tl.load(w_blk, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
        acc += tl.dot(a, b)
        x_blk = tl.advance(x_blk, (0, BLOCK_K))
        w_blk = tl.advance(w_blk, (BLOCK_K, 0))

    bias = tl.load(B_ptr + cols, mask=col_mask, other=0.0).to(tl.float32)
    acc = acc + bias[None, :]

    neg_inf = -float("inf")
    acc = tl.where(col_mask[None, :], acc, neg_inf)

    row_max = tl.max(acc, axis=1)
    row_max = tl.where(row_mask, row_max, 0.0)

    exp2v = tl.exp2((acc - row_max[:, None]) * _LOG2E)
    exp2v = tl.where(row_mask[:, None] & col_mask[None, :], exp2v, 0.0)
    row_sum = tl.sum(exp2v, axis=1)
    row_sum = tl.where(row_mask, row_sum, 0.0)

    out_offs = rows * stride_p + pid_n
    tl.store(PM_ptr + out_offs, row_max, mask=row_mask)
    tl.store(PS_ptr + out_offs, row_sum, mask=row_mask)

    t = tl.load(T_ptr + rows, mask=row_mask, other=0).to(tl.int32)
    in_chunk = (t >= col_start) & (t < (col_start + BLOCK_N)) & row_mask
    mt = (cols[None, :] == t[:, None]) & in_chunk[:, None]
    tlog = tl.sum(tl.where(mt, acc, 0.0), axis=1)
    tl.store(TL_ptr + rows, tlog, mask=in_chunk)


@triton.jit
def _ce_reduce_kernel(
    PM_ptr, PS_ptr, TL_ptr, Out_ptr,
    M: tl.constexpr,
    stride_p,
    N_CHUNKS: tl.constexpr,
):
    row = tl.program_id(0)
    row_mask = row < M

    offs = row * stride_p + tl.arange(0, N_CHUNKS)
    pm = tl.load(PM_ptr + offs, mask=row_mask, other=-float("inf")).to(tl.float32)
    ps = tl.load(PS_ptr + offs, mask=row_mask, other=0.0).to(tl.float32)

    m = tl.max(pm, axis=0)
    m = tl.where(row_mask, m, 0.0)

    scale = tl.exp2((pm - m) * _LOG2E)
    sumexp = tl.sum(ps * scale, axis=0)
    sumexp = tl.where(row_mask, sumexp, 1.0)

    logsumexp = tl.log2(sumexp) * _LN2 + m

    tlog = tl.load(TL_ptr + row, mask=row_mask, other=0.0).to(tl.float32)
    loss = logsumexp - tlog
    tl.store(Out_ptr + row, loss, mask=row_mask)


_buffer_cache = {}

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda):
        logits = X @ W + B
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W.dtype != torch.float16:
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)
    if targets.dtype != torch.int64:
        targets = targets.to(torch.int64)

    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1 or targets.ndim != 1:
        logits = X @ W + B
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    M, K = X.shape
    K2, N = W.shape
    if K2 != K or B.shape[0] != N or targets.shape[0] != M:
        logits = X @ W + B
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    # optimized path assumes K is multiple of 32 for BLOCK_K=32
    if K % 32 != 0:
        logits = X @ W + B
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    BLOCK_M = 16
    BLOCK_N = 128
    BLOCK_K = 32

    n_chunks = triton.cdiv(N, BLOCK_N)

    dev = X.device
    key = (dev.index, M, n_chunks)
    buf = _buffer_cache.get(key, None)
    if buf is None or buf[0].device != dev:
        PM = torch.empty((M, n_chunks), device=dev, dtype=torch.float32)
        PS = torch.empty((M, n_chunks), device=dev, dtype=torch.float32)
        TL = torch.empty((M,), device=dev, dtype=torch.float32)
        _buffer_cache[key] = (PM, PS, TL)
    else:
        PM, PS, TL = buf

    Out = torch.empty((M,), device=dev, dtype=torch.float32)

    grid = (triton.cdiv(M, BLOCK_M), n_chunks)
    _ce_partials_kernel[grid](
        X, W, B, targets,
        PM, PS, TL,
        M,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        PM.stride(0),
        N=N, K=K,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8,
        num_stages=4,
    )

    _ce_reduce_kernel[(M,)](
        PM, PS, TL, Out,
        M,
        PM.stride(0),
        N_CHUNKS=n_chunks,
        num_warps=1,
        num_stages=1,
    )
    return Out
"""
).strip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}