import os
import math
import torch
import triton
import triton.language as tl

_buffer_cache = {}


@triton.jit
def _pq_kernel(
    X_ptr, A_ptr, B_ptr,
    P_ptr, Q_ptr,
    L: tl.constexpr, D: tl.constexpr,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d = pid_d * BD + tl.arange(0, BD)
    dmask = d < D

    p = tl.full((BD,), 1.0, tl.float32)
    q = tl.zeros((BD,), tl.float32)

    base_t = pid_c * CHUNK
    base_offset = base_t * D + d

    tl.multiple_of(D, 16)

    for t in tl.static_range(0, CHUNK):
        offs = base_offset + t * D
        a = tl.load(A_ptr + offs, mask=dmask, other=0).to(tl.float32)
        x = tl.load(X_ptr + offs, mask=dmask, other=0).to(tl.float32)
        b = tl.load(B_ptr + offs, mask=dmask, other=0).to(tl.float32)
        q = a * q + b * x
        p = a * p

    pq_offs = pid_c * D + d
    tl.store(P_ptr + pq_offs, p, mask=dmask)
    tl.store(Q_ptr + pq_offs, q, mask=dmask)


@triton.jit
def _ystart_kernel(
    P_ptr, Q_ptr,
    Y0_ptr,
    NCHUNKS: tl.constexpr, D: tl.constexpr,
    BD: tl.constexpr,
):
    pid_d = tl.program_id(0)

    d = pid_d * BD + tl.arange(0, BD)
    dmask = d < D

    y = tl.zeros((BD,), tl.float32)

    tl.multiple_of(D, 16)

    for c in tl.static_range(0, NCHUNKS):
        offs = c * D + d
        tl.store(Y0_ptr + offs, y, mask=dmask)
        p = tl.load(P_ptr + offs, mask=dmask, other=1.0).to(tl.float32)
        q = tl.load(Q_ptr + offs, mask=dmask, other=0.0).to(tl.float32)
        y = p * y + q


@triton.jit
def _out_kernel(
    X_ptr, A_ptr, B_ptr,
    Y0_ptr,
    Y_ptr,
    L: tl.constexpr, D: tl.constexpr,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d = pid_d * BD + tl.arange(0, BD)
    dmask = d < D

    tl.multiple_of(D, 16)

    y0_offs = pid_c * D + d
    y = tl.load(Y0_ptr + y0_offs, mask=dmask, other=0.0).to(tl.float32)

    base_t = pid_c * CHUNK
    base_offset = base_t * D + d

    for t in tl.static_range(0, CHUNK):
        offs = base_offset + t * D
        a = tl.load(A_ptr + offs, mask=dmask, other=0).to(tl.float32)
        x = tl.load(X_ptr + offs, mask=dmask, other=0).to(tl.float32)
        b = tl.load(B_ptr + offs, mask=dmask, other=0).to(tl.float32)
        y = a * y + b * x
        tl.store(Y_ptr + offs, y.to(tl.float16), mask=dmask)


def _get_temp_buffers(device, n_chunks: int, D: int):
    dev_index = device.index if device.type == "cuda" else -1
    key = (dev_index, n_chunks, D)
    bufs = _buffer_cache.get(key, None)
    if bufs is None or any((not t.is_cuda) or (t.device.index != dev_index) or (t.shape != (n_chunks, D)) for t in bufs):
        P = torch.empty((n_chunks, D), device=device, dtype=torch.float32)
        Q = torch.empty((n_chunks, D), device=device, dtype=torch.float32)
        Y0 = torch.empty((n_chunks, D), device=device, dtype=torch.float32)
        _buffer_cache[key] = (P, Q, Y0)
        return P, Q, Y0
    return bufs


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        raise ValueError("X, A, B must be CUDA tensors")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise ValueError("X, A, B must be float16 tensors")
    if X.ndim != 2 or A.ndim != 2 or B.ndim != 2:
        raise ValueError("X, A, B must be 2D tensors (L, D)")
    if X.shape != A.shape or X.shape != B.shape:
        raise ValueError("X, A, B must have the same shape (L, D)")
    if not X.is_contiguous():
        X = X.contiguous()
    if not A.is_contiguous():
        A = A.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk")
    n_chunks = L // chunk
    n_dblocks = triton.cdiv(D, BD)

    P, Q, Y0 = _get_temp_buffers(X.device, n_chunks, D)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    num_warps = 4 if BD >= 128 else (2 if BD >= 64 else 1)

    grid_pq = (n_chunks, n_dblocks)
    _pq_kernel[grid_pq](
        X, A, B, P, Q,
        L=L, D=D,
        CHUNK=chunk, BD=BD,
        num_warps=num_warps,
        num_stages=2,
    )

    grid_y0 = (n_dblocks,)
    _ystart_kernel[grid_y0](
        P, Q, Y0,
        NCHUNKS=n_chunks, D=D,
        BD=BD,
        num_warps=num_warps,
        num_stages=1,
    )

    grid_out = (n_chunks, n_dblocks)
    _out_kernel[grid_out](
        X, A, B,
        Y0,
        Y,
        L=L, D=D,
        CHUNK=chunk, BD=BD,
        num_warps=num_warps,
        num_stages=2,
    )
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}