import math
from typing import Dict, Optional


KERNEL_CODE = r"""
import math
import torch
import triton
import triton.language as tl

_BUF_CACHE = {}

def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b

def _get_cached_buf(key, shape, device, dtype):
    buf = _BUF_CACHE.get(key, None)
    if buf is None or buf.numel() < (shape[0] * shape[1]) or buf.device != device or buf.dtype != dtype:
        buf = torch.empty(shape, device=device, dtype=dtype)
        _BUF_CACHE[key] = buf
    elif buf.shape != shape:
        buf = buf.view(shape)
        _BUF_CACHE[key] = buf
    return buf

@triton.jit
def _linear_ce_partials_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr,
    max_ptr, sum_ptr, tlog_ptr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_bufm: tl.constexpr, stride_bufn: tl.constexpr,
    M, N,
    K: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BM, BN), dtype=tl.float32)

    # K is assumed compile-time, loop unrolled/static
    for k0 in tl.static_range(0, K, BK):
        offs_k = k0 + tl.arange(0, BK)
        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        a = tl.load(x_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float16)
        b = tl.load(w_ptrs, mask=mask_n[None, :], other=0.0).to(tl.float16)
        acc += tl.dot(a, b)

    bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    logits = acc + bias[None, :]
    logits = tl.where(mask_n[None, :], logits, -float("inf"))

    tile_max = tl.max(logits, axis=1)
    exps = tl.exp(logits - tile_max[:, None])
    exps = tl.where(mask_n[None, :], exps, 0.0)
    tile_sum = tl.sum(exps, axis=1)

    t = tl.load(T_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)
    n_start = pid_n * BN
    in_tile = (t >= n_start) & (t < n_start + BN)
    idx = t - n_start  # int32
    cols = tl.arange(0, BN)[None, :]
    pick = in_tile[:, None] & (cols == idx[:, None]) & mask_n[None, :]
    tlog = tl.sum(tl.where(pick, logits, 0.0), axis=1)
    tlog = tl.where(mask_m, tlog, 0.0)

    out_ptrs = (offs_m * stride_bufm + pid_n * stride_bufn)
    tl.store(max_ptr + out_ptrs, tile_max, mask=mask_m)
    tl.store(sum_ptr + out_ptrs, tile_sum, mask=mask_m)
    tl.store(tlog_ptr + out_ptrs, tlog, mask=mask_m)

@triton.jit
def _reduce_ce_kernel(
    max_ptr, sum_ptr, tlog_ptr,
    out_ptr,
    stride_bufm: tl.constexpr, stride_bufn: tl.constexpr,
    M,
    NUM_TILES: tl.constexpr,
    BM: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BM + tl.arange(0, BM)
    mask_m = offs_m < M

    run_max = tl.where(mask_m, -float("inf"), 0.0).to(tl.float32)
    run_sum = tl.where(mask_m, 0.0, 1.0).to(tl.float32)
    tlog = tl.zeros((BM,), dtype=tl.float32)

    base = offs_m * stride_bufm
    for j in tl.static_range(0, NUM_TILES):
        tile_max = tl.load(max_ptr + base + j * stride_bufn, mask=mask_m, other=0.0).to(tl.float32)
        tile_sum = tl.load(sum_ptr + base + j * stride_bufn, mask=mask_m, other=0.0).to(tl.float32)
        tile_tlog = tl.load(tlog_ptr + base + j * stride_bufn, mask=mask_m, other=0.0).to(tl.float32)

        new_max = tl.maximum(run_max, tile_max)
        run_sum = run_sum * tl.exp(run_max - new_max) + tile_sum * tl.exp(tile_max - new_max)
        run_max = new_max
        tlog += tile_tlog

    lse = tl.log(run_sum) + run_max
    loss = lse - tlog
    tl.store(out_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    assert X.ndim == 2 and W.ndim == 2 and B.ndim == 1 and targets.ndim == 1
    M, K = X.shape
    Kw, N = W.shape
    assert Kw == K
    assert B.shape[0] == N
    assert targets.shape[0] == M

    # Tuned constants (compile-time)
    BN = 128
    BK = 32
    BM1 = 16
    BM2 = 128

    # K must be compile-time for the dot loop in this kernel
    # (this benchmark typically uses K=4096)
    num_tiles = _ceil_div(N, BN)

    dev = X.device
    max_buf = _get_cached_buf(("max", dev.index if dev.type == "cuda" else -1, M, num_tiles), (M, num_tiles), dev, torch.float32)
    sum_buf = _get_cached_buf(("sum", dev.index if dev.type == "cuda" else -1, M, num_tiles), (M, num_tiles), dev, torch.float32)
    tlog_buf = _get_cached_buf(("tlog", dev.index if dev.type == "cuda" else -1, M, num_tiles), (M, num_tiles), dev, torch.float32)

    out = torch.empty((M,), device=dev, dtype=torch.float32)

    grid1 = (triton.cdiv(M, BM1), num_tiles)
    _linear_ce_partials_kernel[grid1](
        X, W, B, targets,
        max_buf, sum_buf, tlog_buf,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        max_buf.stride(0), max_buf.stride(1),
        M, N,
        K=K, BM=BM1, BN=BN, BK=BK,
        num_warps=8, num_stages=4
    )

    grid2 = (triton.cdiv(M, BM2),)
    _reduce_ce_kernel[grid2](
        max_buf, sum_buf, tlog_buf,
        out,
        max_buf.stride(0), max_buf.stride(1),
        M,
        NUM_TILES=num_tiles,
        BM=BM2,
        num_warps=4, num_stages=2
    )
    return out

__all__ = ["fused_linear_ce"]
"""


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"code": KERNEL_CODE}
