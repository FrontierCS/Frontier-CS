import os
import sys
import inspect
from typing import Dict, Tuple, Optional

import torch
import triton
import triton.language as tl

_TMP_CACHE: Dict[Tuple[int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _next_pow2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()


def _get_temp_buffers(device: torch.device, M: int, rblocks: int):
    dev_index = device.index if device.type == "cuda" else -1
    key = (dev_index, M, rblocks)
    buf = _TMP_CACHE.get(key, None)
    if buf is None or buf[0].device != device:
        max_buf = torch.empty((M, rblocks), device=device, dtype=torch.float32)
        sum_buf = torch.empty((M, rblocks), device=device, dtype=torch.float32)
        tlogit_buf = torch.empty((M,), device=device, dtype=torch.float32)
        _TMP_CACHE[key] = (max_buf, sum_buf, tlogit_buf)
        return max_buf, sum_buf, tlogit_buf
    max_buf, sum_buf, tlogit_buf = buf
    if max_buf.shape[0] != M or max_buf.shape[1] != rblocks:
        max_buf = torch.empty((M, rblocks), device=device, dtype=torch.float32)
        sum_buf = torch.empty((M, rblocks), device=device, dtype=torch.float32)
        tlogit_buf = torch.empty((M,), device=device, dtype=torch.float32)
        _TMP_CACHE[key] = (max_buf, sum_buf, tlogit_buf)
        return max_buf, sum_buf, tlogit_buf
    return max_buf, sum_buf, tlogit_buf


@triton.jit
def _linear_ce_partials_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    T_ptr,
    out_max_ptr,
    out_sum_ptr,
    out_tlogit_ptr,
    M: tl.constexpr,
    N,
    K: tl.constexpr,
    stride_xm: tl.constexpr,
    stride_xk: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_wn: tl.constexpr,
    stride_om: tl.constexpr,
    stride_on: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_it = K // BLOCK_K
    for i in tl.static_range(0, k_it):
        offs_k = i * BLOCK_K + tl.arange(0, BLOCK_K)
        x = tl.load(
            X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
            mask=mask_m[:, None],
            other=0.0,
        ).to(tl.float16)
        w = tl.load(
            W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
            mask=mask_n[None, :],
            other=0.0,
        ).to(tl.float16)
        acc += tl.dot(x, w)

    b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    logits = acc + b[None, :]
    logits = tl.where(mask_n[None, :], logits, -1.0e20)

    block_max = tl.max(logits, axis=1)
    exp_logits = tl.exp(logits - block_max[:, None])
    block_sum = tl.sum(exp_logits, axis=1)

    out_idx = offs_m * stride_om + pid_n * stride_on
    tl.store(out_max_ptr + out_idx, block_max, mask=mask_m)
    tl.store(out_sum_ptr + out_idx, block_sum, mask=mask_m)

    targets = tl.load(T_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)
    col_start = pid_n * BLOCK_N
    in_tile = (targets >= col_start) & (targets < (col_start + BLOCK_N))
    idx = targets - col_start
    cols = tl.arange(0, BLOCK_N)[None, :]
    mask_t = in_tile[:, None] & (cols == idx[:, None]) & mask_m[:, None] & mask_n[None, :]
    tlogit = tl.sum(tl.where(mask_t, logits, 0.0), axis=1)
    tl.store(out_tlogit_ptr + offs_m, tlogit, mask=mask_m & in_tile)


@triton.jit
def _linear_ce_reduce_kernel(
    in_max_ptr,
    in_sum_ptr,
    in_tlogit_ptr,
    out_loss_ptr,
    M,
    NB_ACTUAL,
    stride_im: tl.constexpr,
    stride_in: tl.constexpr,
    RBLOCKS: tl.constexpr,
):
    pid = tl.program_id(0)
    if pid >= M:
        return

    offs = tl.arange(0, RBLOCKS)
    mask = offs < NB_ACTUAL

    maxs = tl.load(in_max_ptr + pid * stride_im + offs * stride_in, mask=mask, other=-1.0e20).to(tl.float32)
    row_max = tl.max(maxs, axis=0)

    sums = tl.load(in_sum_ptr + pid * stride_im + offs * stride_in, mask=mask, other=0.0).to(tl.float32)
    total = tl.sum(sums * tl.exp(maxs - row_max), axis=0)
    total = tl.maximum(total, 1.0e-20)
    lse = row_max + tl.log(total)

    tlogit = tl.load(in_tlogit_ptr + pid).to(tl.float32)
    tl.store(out_loss_ptr + pid, lse - tlogit)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda):
        logits = X.float() @ W.float() + B.float()
        return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

    assert X.dtype == torch.float16 and W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    assert X.ndim == 2 and W.ndim == 2 and B.ndim == 1 and targets.ndim == 1

    M, K = X.shape
    K2, N = W.shape
    assert K == K2
    assert B.numel() == N
    assert targets.numel() == M

    Xc = X
    Wc = W
    Bc = B
    Tc = targets

    if not Xc.is_contiguous():
        Xc = Xc.contiguous()
    if not Wc.is_contiguous():
        Wc = Wc.contiguous()
    if not Bc.is_contiguous():
        Bc = Bc.contiguous()
    if not Tc.is_contiguous():
        Tc = Tc.contiguous()

    BLOCK_N = 128
    nblocks_actual = triton.cdiv(N, BLOCK_N)
    rblocks = _next_pow2(nblocks_actual)

    out_max, out_sum, out_tlogit = _get_temp_buffers(Xc.device, M, rblocks)
    out_loss = torch.empty((M,), device=Xc.device, dtype=torch.float32)

    stride_xm, stride_xk = Xc.stride()
    stride_wk, stride_wn = Wc.stride()
    stride_om, stride_on = out_max.stride()

    BLOCK_M = 16
    BLOCK_K = 64
    num_warps = 8
    num_stages = 4

    grid = (triton.cdiv(M, BLOCK_M), nblocks_actual)
    _linear_ce_partials_kernel[grid](
        Xc,
        Wc,
        Bc,
        Tc,
        out_max,
        out_sum,
        out_tlogit,
        M=M,
        N=N,
        K=K,
        stride_xm=stride_xm,
        stride_xk=stride_xk,
        stride_wk=stride_wk,
        stride_wn=stride_wn,
        stride_om=stride_om,
        stride_on=stride_on,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    _linear_ce_reduce_kernel[(M,)](
        out_max,
        out_sum,
        out_tlogit,
        out_loss,
        M=M,
        NB_ACTUAL=nblocks_actual,
        stride_im=stride_om,
        stride_in=stride_on,
        RBLOCKS=rblocks,
        num_warps=1,
        num_stages=1,
    )

    return out_loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        parts = []
        parts.append("import torch\nimport triton\nimport triton.language as tl\n\n")
        parts.append("_TMP_CACHE = {}\n\n")
        for obj in (
            _next_pow2,
            _get_temp_buffers,
            _linear_ce_partials_kernel,
            _linear_ce_reduce_kernel,
            fused_linear_ce,
        ):
            parts.append(inspect.getsource(obj))
            parts.append("\n\n")
        return {"code": "".join(parts)}
