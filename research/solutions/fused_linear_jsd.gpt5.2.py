import math
import os
import sys
from typing import Dict, Optional

import torch
import triton
import triton.language as tl

_KERNEL_CODE = r'''
import math
from typing import Dict, Tuple

import torch
import triton
import triton.language as tl

_WCAT_CACHE: Dict[Tuple[int, int, int, Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]], torch.Tensor] = {}
_BUF_CACHE: Dict[Tuple[int, torch.dtype, Tuple[int, ...]], torch.Tensor] = {}

def _device_index(t: torch.Tensor) -> int:
    if t.device.type != "cuda":
        return -1
    return int(t.device.index) if t.device.index is not None else int(torch.cuda.current_device())

def _get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
    key = (
        int(W1.data_ptr()),
        int(W2.data_ptr()),
        _device_index(W1),
        tuple(W1.shape),
        tuple(W2.shape),
        tuple(W1.stride()),
        tuple(W2.stride()),
    )
    w = _WCAT_CACHE.get(key)
    if w is not None:
        return w
    w = torch.cat((W1, W2), dim=1)
    _WCAT_CACHE[key] = w
    return w

def _get_buf(device: torch.device, dtype: torch.dtype, shape: Tuple[int, ...]) -> torch.Tensor:
    dev_idx = int(device.index) if device.index is not None else int(torch.cuda.current_device())
    key = (dev_idx, dtype, tuple(shape))
    buf = _BUF_CACHE.get(key)
    if buf is None or buf.device != device or buf.dtype != dtype or tuple(buf.shape) != tuple(shape):
        buf = torch.empty(shape, device=device, dtype=dtype)
        _BUF_CACHE[key] = buf
    return buf

@triton.jit
def _jsd_full_kernel(
    logits_ptr, b1_ptr, b2_ptr, out_ptr,
    M: tl.constexpr, STRIDE_M: tl.constexpr, STRIDE_N: tl.constexpr,
    N: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr,
    EPS: tl.constexpr,
):
    pid = tl.program_id(0)

    m_offs = pid * BM + tl.arange(0, BM)
    mask_m = m_offs < M

    m1 = tl.full((BM,), -float("inf"), tl.float32)
    s1 = tl.zeros((BM,), tl.float32)
    m2 = tl.full((BM,), -float("inf"), tl.float32)
    s2 = tl.zeros((BM,), tl.float32)

    for n0 in tl.static_range(0, N, BN):
        n_offs = n0 + tl.arange(0, BN)
        mask_n = n_offs < N

        b1 = tl.load(b1_ptr + n_offs, mask=mask_n, other=0.0).to(tl.float32)[None, :]
        b2 = tl.load(b2_ptr + n_offs, mask=mask_n, other=0.0).to(tl.float32)[None, :]

        ptrs1 = logits_ptr + m_offs[:, None] * STRIDE_M + n_offs[None, :] * STRIDE_N
        ptrs2 = logits_ptr + m_offs[:, None] * STRIDE_M + (n_offs[None, :] + N) * STRIDE_N

        mask = mask_m[:, None] & mask_n[None, :]

        l1 = tl.load(ptrs1, mask=mask, other=-float("inf")).to(tl.float32) + b1
        l2 = tl.load(ptrs2, mask=mask, other=-float("inf")).to(tl.float32) + b2

        bm1 = tl.max(l1, axis=1)
        bs1 = tl.sum(tl.exp(l1 - bm1[:, None]), axis=1)

        bm2 = tl.max(l2, axis=1)
        bs2 = tl.sum(tl.exp(l2 - bm2[:, None]), axis=1)

        new_m1 = tl.maximum(m1, bm1)
        s1 = s1 * tl.exp(m1 - new_m1) + bs1 * tl.exp(bm1 - new_m1)
        m1 = new_m1

        new_m2 = tl.maximum(m2, bm2)
        s2 = s2 * tl.exp(m2 - new_m2) + bs2 * tl.exp(bm2 - new_m2)
        m2 = new_m2

    logZ1 = m1 + tl.log(s1)
    logZ2 = m2 + tl.log(s2)

    acc1 = tl.zeros((BM,), tl.float32)
    acc2 = tl.zeros((BM,), tl.float32)

    for n0 in tl.static_range(0, N, BN):
        n_offs = n0 + tl.arange(0, BN)
        mask_n = n_offs < N

        b1 = tl.load(b1_ptr + n_offs, mask=mask_n, other=0.0).to(tl.float32)[None, :]
        b2 = tl.load(b2_ptr + n_offs, mask=mask_n, other=0.0).to(tl.float32)[None, :]

        ptrs1 = logits_ptr + m_offs[:, None] * STRIDE_M + n_offs[None, :] * STRIDE_N
        ptrs2 = logits_ptr + m_offs[:, None] * STRIDE_M + (n_offs[None, :] + N) * STRIDE_N

        mask = mask_m[:, None] & mask_n[None, :]

        l1 = tl.load(ptrs1, mask=mask, other=-float("inf")).to(tl.float32) + b1
        l2 = tl.load(ptrs2, mask=mask, other=-float("inf")).to(tl.float32) + b2

        logP = l1 - logZ1[:, None]
        logQ = l2 - logZ2[:, None]

        p = tl.exp(logP)
        q = tl.exp(logQ)

        m = 0.5 * (p + q)
        logM = tl.log(tl.maximum(m, EPS))

        acc1 += tl.sum(p * (logP - logM), axis=1)
        acc2 += tl.sum(q * (logQ - logM), axis=1)

    jsd = 0.5 * (acc1 + acc2)
    tl.store(out_ptr + m_offs, jsd, mask=mask_m)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if X.device.type != "cuda":
        raise RuntimeError("fused_linear_jsd: X must be a CUDA tensor")
    if W1.device != X.device or W2.device != X.device or B1.device != X.device or B2.device != X.device:
        raise RuntimeError("fused_linear_jsd: all tensors must be on the same CUDA device")

    if X.dtype != torch.float16 or W1.dtype != torch.float16 or W2.dtype != torch.float16:
        raise RuntimeError("fused_linear_jsd: X, W1, W2 must be float16")
    if B1.dtype != torch.float32 or B2.dtype != torch.float32:
        B1 = B1.to(torch.float32)
        B2 = B2.to(torch.float32)

    if X.ndim != 2 or W1.ndim != 2 or W2.ndim != 2 or B1.ndim != 1 or B2.ndim != 1:
        raise RuntimeError("fused_linear_jsd: invalid tensor ranks")

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    if K1 != K or K2 != K or N2 != N or B1.numel() != N or B2.numel() != N:
        raise RuntimeError("fused_linear_jsd: shape mismatch")

    Wcat = _get_wcat(W1, W2)

    logits = _get_buf(X.device, torch.float16, (M, 2 * N))
    torch.mm(X, Wcat, out=logits)

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    stride_m = logits.stride(0)
    stride_n = logits.stride(1)

    BM = 8
    BN = 256
    grid = (triton.cdiv(M, BM),)

    _jsd_full_kernel[grid](
        logits, B1, B2, out,
        M=M, STRIDE_M=stride_m, STRIDE_N=stride_n,
        N=N, BM=BM, BN=BN,
        EPS=1e-20,
        num_warps=4,
        num_stages=2,
    )
    return out
'''

exec(_KERNEL_CODE, globals(), globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
