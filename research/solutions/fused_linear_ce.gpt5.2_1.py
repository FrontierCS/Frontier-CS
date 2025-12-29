import textwrap


KERNEL_CODE = textwrap.dedent(
    r"""
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _linear_ce_partials_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    T_ptr,
    PMAX_ptr,
    PSUM_ptr,
    TLOG_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm: tl.constexpr,
    stride_xk: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_wn: tl.constexpr,
    stride_pbn: tl.constexpr,
    stride_pm: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    NEG_INF: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    a_ptr = tl.make_block_ptr(
        base=X_ptr,
        shape=(M, K),
        strides=(stride_xm, stride_xk),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_ptr = tl.make_block_ptr(
        base=W_ptr,
        shape=(K, N),
        strides=(stride_wk, stride_wn),
        offsets=(0, pid_n * BLOCK_N),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for _ in tl.static_range(0, (K + BLOCK_K - 1) // BLOCK_K):
        a = tl.load(a_ptr, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
        b = tl.load(b_ptr, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
        acc = tl.dot(a, b, acc=acc)
        a_ptr = tl.advance(a_ptr, (0, BLOCK_K))
        b_ptr = tl.advance(b_ptr, (BLOCK_K, 0))

    col_mask = offs_n < N
    bias = tl.load(B_ptr + offs_n, mask=col_mask, other=0.0).to(tl.float32)
    acc = acc + bias[None, :]

    acc_masked = tl.where(col_mask[None, :], acc, NEG_INF)
    bmax = tl.max(acc_masked, axis=1)
    ex = tl.exp(acc_masked - bmax[:, None])
    bsum = tl.sum(ex, axis=1)

    row_mask = offs_m < M
    p_offs = pid_n * stride_pbn + offs_m * stride_pm
    tl.store(PMAX_ptr + p_offs, bmax, mask=row_mask)
    tl.store(PSUM_ptr + p_offs, bsum, mask=row_mask)

    t = tl.load(T_ptr + offs_m, mask=row_mask, other=0).to(tl.int32)
    start = pid_n * BLOCK_N
    in_range = row_mask & (t >= start) & (t < (start + BLOCK_N))
    tcol = t - start

    bn_ids = tl.arange(0, BLOCK_N)[None, :]
    match = bn_ids == tcol[:, None]
    tlog = tl.sum(tl.where(match, acc, 0.0), axis=1)
    tl.store(TLOG_ptr + offs_m, tlog, mask=in_range)


@triton.jit
def _linear_ce_reduce_kernel(
    PMAX_ptr,
    PSUM_ptr,
    TLOG_ptr,
    OUT_ptr,
    M: tl.constexpr,
    stride_pbn: tl.constexpr,
    stride_pm: tl.constexpr,
    NUM_BLOCKS_N: tl.constexpr,
    BLOCK_RM: tl.constexpr,
    NEG_INF: tl.constexpr,
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_RM + tl.arange(0, BLOCK_RM)
    row_mask = offs_m < M

    m = tl.full((BLOCK_RM,), NEG_INF, tl.float32)
    s = tl.zeros((BLOCK_RM,), dtype=tl.float32)

    for bn in tl.static_range(0, NUM_BLOCKS_N):
        p_offs = bn * stride_pbn + offs_m * stride_pm
        bmax = tl.load(PMAX_ptr + p_offs, mask=row_mask, other=NEG_INF).to(tl.float32)
        bsum = tl.load(PSUM_ptr + p_offs, mask=row_mask, other=0.0).to(tl.float32)
        new_m = tl.maximum(m, bmax)
        s = s * tl.exp(m - new_m) + bsum * tl.exp(bmax - new_m)
        m = new_m

    tlog = tl.load(TLOG_ptr + offs_m, mask=row_mask, other=0.0).to(tl.float32)
    loss = tl.log(s) + m - tlog
    tl.store(OUT_ptr + offs_m, loss, mask=row_mask)


_ce_cache = {}


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16
    assert B.dtype in (torch.float32, torch.float16, torch.bfloat16)
    assert targets.dtype == torch.int64

    M, K = X.shape
    Kw, N = W.shape
    assert Kw == K
    assert B.numel() == N
    assert targets.numel() == M

    if B.dtype != torch.float32:
        B = B.float()

    BLOCK_M = 16
    BLOCK_N = 128
    BLOCK_K = 32
    NEG_INF = -1.0e20

    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)

    key = (X.device, M, grid_n)
    bufs = _ce_cache.get(key)
    if bufs is None or bufs[0].shape != (grid_n, M):
        pmax = torch.empty((grid_n, M), device=X.device, dtype=torch.float32)
        psum = torch.empty((grid_n, M), device=X.device, dtype=torch.float32)
        tlog = torch.empty((M,), device=X.device, dtype=torch.float32)
        _ce_cache[key] = (pmax, psum, tlog)
    else:
        pmax, psum, tlog = bufs

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    _linear_ce_partials_kernel[(grid_m, grid_n)](
        X, W, B, targets,
        pmax, psum, tlog,
        M=M, N=N, K=K,
        stride_xm=X.stride(0), stride_xk=X.stride(1),
        stride_wk=W.stride(0), stride_wn=W.stride(1),
        stride_pbn=pmax.stride(0), stride_pm=pmax.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K, NEG_INF=NEG_INF,
        num_warps=4,
        num_stages=3,
    )

    BLOCK_RM = 128
    _linear_ce_reduce_kernel[(triton.cdiv(M, BLOCK_RM),)](
        pmax, psum, tlog, out,
        M=M,
        stride_pbn=pmax.stride(0), stride_pm=pmax.stride(1),
        NUM_BLOCKS_N=grid_n,
        BLOCK_RM=BLOCK_RM,
        NEG_INF=NEG_INF,
        num_warps=4,
        num_stages=1,
    )
    return out
"""
).strip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}