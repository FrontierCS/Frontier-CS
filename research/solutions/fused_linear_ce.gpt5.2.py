import os
import math
import inspect
from typing import Dict, Any, Optional


KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

# ----------------------------- Kernels -----------------------------

@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 128, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_N": 256, "BLOCK_K": 64}, num_warps=8, num_stages=4),
    ],
    key=["N", "K"],
)
@triton.jit
def _linear_ce_tiles_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr,
    tile_max_ptr, tile_sum_ptr, tlogit_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_tm: tl.constexpr,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_t = tl.program_id(1)
    row_ok = pid_m < M

    col_start = pid_t * BLOCK_N
    cols = col_start + tl.arange(0, BLOCK_N)
    col_ok = cols < N

    # Load target
    t = tl.load(T_ptr + pid_m, mask=row_ok, other=0).to(tl.int32)

    # Accumulator
    acc = tl.zeros([BLOCK_N], dtype=tl.float32)

    # Dot: (1, K) @ (K, BLOCK_N) -> (BLOCK_N,)
    # Assume typical contiguous layout but keep strides.
    x_row_ptr = X_ptr + pid_m * stride_xm

    # K is constexpr; allow unrolling
    for k0 in tl.static_range(0, K, BLOCK_K):
        k = k0 + tl.arange(0, BLOCK_K)
        k_ok = k < K

        x = tl.load(x_row_ptr + k * stride_xk, mask=row_ok & k_ok, other=0.0).to(tl.float16)
        w = tl.load(
            W_ptr + (k[:, None] * stride_wk + cols[None, :] * stride_wn),
            mask=k_ok[:, None] & col_ok[None, :],
            other=0.0,
        ).to(tl.float16)

        acc += tl.dot(x[None, :], w)[0, :]

    b = tl.load(B_ptr + cols, mask=col_ok, other=0.0).to(tl.float32)
    acc = acc + b

    # Mask out-of-range columns as -inf
    acc_m = tl.where(col_ok, acc, -float("inf"))

    block_max = tl.max(acc_m, axis=0)
    # sum(exp(x - block_max)) within tile
    block_sum = tl.sum(tl.exp(acc_m - block_max), axis=0)

    # Store tile stats into [M, TILES_MAX] layout; tile index is pid_t
    tl.store(tile_max_ptr + pid_m * stride_tm + pid_t, block_max, mask=row_ok)
    tl.store(tile_sum_ptr + pid_m * stride_tm + pid_t, block_sum, mask=row_ok)

    # Store target logit (only one tile should match)
    hit = cols == t
    has = tl.sum(hit.to(tl.int32), axis=0) > 0
    tlog = tl.sum(tl.where(hit, acc, 0.0), axis=0)
    tl.store(tlogit_ptr + pid_m, tlog, mask=row_ok & has)


@triton.jit
def _reduce_tiles_kernel(
    tile_max_ptr, tile_sum_ptr, tlogit_ptr, out_ptr,
    M: tl.constexpr,
    stride_tm: tl.constexpr,
    TILES: tl.constexpr,
    BLOCK_T: tl.constexpr,
):
    pid_m = tl.program_id(0)
    row_ok = pid_m < M

    offs = tl.arange(0, BLOCK_T)
    m = tl.load(tile_max_ptr + pid_m * stride_tm + offs, mask=row_ok & (offs < TILES), other=-float("inf"))
    row_max = tl.max(m, axis=0)

    s = tl.load(tile_sum_ptr + pid_m * stride_tm + offs, mask=row_ok & (offs < TILES), other=0.0)
    total = tl.sum(s * tl.exp(m - row_max), axis=0)

    tlog = tl.load(tlogit_ptr + pid_m, mask=row_ok, other=0.0).to(tl.float32)
    loss = (tl.log(total) + row_max) - tlog

    tl.store(out_ptr + pid_m, loss, mask=row_ok)


# ----------------------------- Python API -----------------------------

_BUFFER_CACHE = {}

def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b

def _next_pow2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not X.is_cuda or not W.is_cuda or not B.is_cuda or not targets.is_cuda:
        logits = X @ W
        logits = logits + B
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype in (torch.int64, torch.int32), "targets must be int64/int32"
    assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1 and targets.dim() == 1

    M, K = X.shape
    K2, N = W.shape
    assert K2 == K, "W shape mismatch"
    assert B.shape[0] == N, "B shape mismatch"
    assert targets.shape[0] == M, "targets shape mismatch"

    # Allocate for worst-case tiles across autotuned BLOCK_N values (min BLOCK_N = 128)
    BN_MIN = 128
    tiles_max = _ceil_div(N, BN_MIN)

    dev = X.device
    key = (dev.index, M, tiles_max)

    buf = _BUFFER_CACHE.get(key)
    if buf is None or buf[0].numel() != (M * tiles_max):
        tile_max = torch.empty((M, tiles_max), device=dev, dtype=torch.float32)
        tile_sum = torch.empty((M, tiles_max), device=dev, dtype=torch.float32)
        tlogit = torch.empty((M,), device=dev, dtype=torch.float32)
        _BUFFER_CACHE[key] = (tile_max, tile_sum, tlogit)
    else:
        tile_max, tile_sum, tlogit = buf

    # Init buffers (small)
    tile_max.fill_(-float("inf"))
    tile_sum.zero_()
    tlogit.zero_()

    # Launch tiles kernel: grid tiles depend on BLOCK_N (autotuned), but output fits in tiles_max
    grid = lambda meta: (M, triton.cdiv(N, meta["BLOCK_N"]))
    _linear_ce_tiles_kernel[grid](
        X, W, B, targets,
        tile_max, tile_sum, tlogit,
        M=M, N=N, K=K,
        stride_xm=X.stride(0), stride_xk=X.stride(1),
        stride_wk=W.stride(0), stride_wn=W.stride(1),
        stride_tm=tile_max.stride(0),
    )

    # Reduce
    out = torch.empty((M,), device=dev, dtype=torch.float32)

    BLOCK_T = _next_pow2(tiles_max)
    if BLOCK_T < 32:
        BLOCK_T = 32
    if BLOCK_T > 256:
        # Safety: cap; for expected N this won't trigger.
        BLOCK_T = 256

    _reduce_tiles_kernel[(M,)](
        tile_max, tile_sum, tlogit, out,
        M=M,
        stride_tm=tile_max.stride(0),
        TILES=tiles_max,
        BLOCK_T=BLOCK_T,
        num_warps=4 if BLOCK_T <= 64 else 8,
    )
    return out
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}