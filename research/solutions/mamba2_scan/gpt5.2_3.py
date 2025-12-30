import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl

__all__ = ["chunk_scan"]

_CACHE = {}

def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b

@triton.jit
def _stage1_ybar_pprod_kernel(
    X_ptr, A_ptr, B_ptr,
    Y_ptr, Ppos_ptr,
    Pchunk_ptr, Qchunk_ptr,
    stride_x0: tl.constexpr, stride_x1: tl.constexpr,
    stride_a0: tl.constexpr, stride_a1: tl.constexpr,
    stride_b0: tl.constexpr, stride_b1: tl.constexpr,
    stride_y0: tl.constexpr, stride_y1: tl.constexpr,
    stride_pp0: tl.constexpr, stride_pp1: tl.constexpr,
    stride_pc0: tl.constexpr, stride_pc1: tl.constexpr,
    stride_qc0: tl.constexpr, stride_qc1: tl.constexpr,
    D: tl.constexpr,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_db = tl.program_id(1)

    offs_d = pid_db * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    tl.multiple_of(offs_d, 8)

    y = tl.zeros([BD], dtype=tl.float32)
    p = tl.full([BD], 1.0, dtype=tl.float32)

    base_l = pid_chunk * CHUNK

    for t in tl.static_range(0, CHUNK):
        l = base_l + t

        off_x = l * stride_x0 + offs_d * stride_x1
        off_a = l * stride_a0 + offs_d * stride_a1
        off_b = l * stride_b0 + offs_d * stride_b1
        off_y = l * stride_y0 + offs_d * stride_y1
        off_pp = l * stride_pp0 + offs_d * stride_pp1

        x = tl.load(X_ptr + off_x, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + off_a, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + off_b, mask=mask_d, other=0.0).to(tl.float32)

        y = a * y + b * x
        p = p * a

        tl.store(Y_ptr + off_y, y.to(tl.float16), mask=mask_d)
        tl.store(Ppos_ptr + off_pp, p.to(tl.float16), mask=mask_d)

    off_pc = pid_chunk * stride_pc0 + offs_d * stride_pc1
    off_qc = pid_chunk * stride_qc0 + offs_d * stride_qc1
    tl.store(Pchunk_ptr + off_pc, p.to(tl.float16), mask=mask_d)
    tl.store(Qchunk_ptr + off_qc, y.to(tl.float16), mask=mask_d)

@triton.jit
def _state_scan_kernel(
    Pchunk_ptr, Qchunk_ptr,
    State_ptr,
    stride_pc0: tl.constexpr, stride_pc1: tl.constexpr,
    stride_qc0: tl.constexpr, stride_qc1: tl.constexpr,
    stride_s0: tl.constexpr, stride_s1: tl.constexpr,
    D: tl.constexpr,
    NCHUNKS: tl.constexpr,
    BD: tl.constexpr,
):
    pid_db = tl.program_id(0)
    offs_d = pid_db * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    tl.multiple_of(offs_d, 8)

    state = tl.zeros([BD], dtype=tl.float32)

    for k in tl.static_range(0, NCHUNKS):
        off_s = k * stride_s0 + offs_d * stride_s1
        tl.store(State_ptr + off_s, state, mask=mask_d)

        off_pc = k * stride_pc0 + offs_d * stride_pc1
        off_qc = k * stride_qc0 + offs_d * stride_qc1

        p = tl.load(Pchunk_ptr + off_pc, mask=mask_d, other=1.0).to(tl.float32)
        q = tl.load(Qchunk_ptr + off_qc, mask=mask_d, other=0.0).to(tl.float32)

        state = p * state + q

@triton.jit
def _apply_state_kernel(
    Y_ptr, Ppos_ptr,
    State_ptr,
    stride_y0: tl.constexpr, stride_y1: tl.constexpr,
    stride_pp0: tl.constexpr, stride_pp1: tl.constexpr,
    stride_s0: tl.constexpr, stride_s1: tl.constexpr,
    D: tl.constexpr,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_db = tl.program_id(1)

    offs_d = pid_db * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    tl.multiple_of(offs_d, 8)

    off_s = pid_chunk * stride_s0 + offs_d * stride_s1
    s = tl.load(State_ptr + off_s, mask=mask_d, other=0.0).to(tl.float32)

    base_l = pid_chunk * CHUNK

    for t in tl.static_range(0, CHUNK):
        l = base_l + t
        off_y = l * stride_y0 + offs_d * stride_y1
        off_pp = l * stride_pp0 + offs_d * stride_pp1

        ybar = tl.load(Y_ptr + off_y, mask=mask_d, other=0.0).to(tl.float32)
        p = tl.load(Ppos_ptr + off_pp, mask=mask_d, other=0.0).to(tl.float32)

        y = ybar + p * s
        tl.store(Y_ptr + off_y, y.to(tl.float16), mask=mask_d)

def _get_cache(L: int, D: int, device: torch.device, chunk: int, BD: int):
    key = (device.index, L, D, chunk, BD)
    buf = _CACHE.get(key, None)
    if buf is not None:
        return buf
    nchunks = L // chunk
    ppos = torch.empty((L, D), device=device, dtype=torch.float16)
    pchunk = torch.empty((nchunks, D), device=device, dtype=torch.float16)
    qchunk = torch.empty((nchunks, D), device=device, dtype=torch.float16)
    state = torch.empty((nchunks, D), device=device, dtype=torch.float32)
    buf = (ppos, pchunk, qchunk, state)
    _CACHE[key] = buf
    return buf

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if X.ndim != 2 or A.ndim != 2 or B.ndim != 2:
        raise ValueError("X, A, B must be 2D tensors of shape (L, D)")
    if X.shape != A.shape or X.shape != B.shape:
        raise ValueError("X, A, B must have the same shape (L, D)")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise TypeError("X, A, B must be torch.float16")
    if not X.is_cuda or not A.is_cuda or not B.is_cuda:
        raise ValueError("X, A, B must be CUDA tensors")

    L, D = X.shape
    if (L % chunk) != 0:
        raise ValueError("L must be divisible by chunk")

    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    ppos, pchunk, qchunk, state = _get_cache(L, D, X.device, chunk, BD)
    nchunks = L // chunk
    ndb = _ceil_div(D, BD)

    stride_x0, stride_x1 = X.stride()
    stride_a0, stride_a1 = A.stride()
    stride_b0, stride_b1 = B.stride()
    stride_y0, stride_y1 = Y.stride()
    stride_pp0, stride_pp1 = ppos.stride()
    stride_pc0, stride_pc1 = pchunk.stride()
    stride_qc0, stride_qc1 = qchunk.stride()
    stride_s0, stride_s1 = state.stride()

    warps = 4 if BD <= 128 else 8

    _stage1_ybar_pprod_kernel[(nchunks, ndb)](
        X, A, B,
        Y, ppos,
        pchunk, qchunk,
        stride_x0, stride_x1,
        stride_a0, stride_a1,
        stride_b0, stride_b1,
        stride_y0, stride_y1,
        stride_pp0, stride_pp1,
        stride_pc0, stride_pc1,
        stride_qc0, stride_qc1,
        D=D,
        CHUNK=chunk,
        BD=BD,
        num_warps=warps,
        num_stages=2,
    )

    _state_scan_kernel[(ndb,)](
        pchunk, qchunk,
        state,
        stride_pc0, stride_pc1,
        stride_qc0, stride_qc1,
        stride_s0, stride_s1,
        D=D,
        NCHUNKS=nchunks,
        BD=BD,
        num_warps=4,
        num_stages=1,
    )

    _apply_state_kernel[(nchunks, ndb)](
        Y, ppos,
        state,
        stride_y0, stride_y1,
        stride_pp0, stride_pp1,
        stride_s0, stride_s1,
        D=D,
        CHUNK=chunk,
        BD=BD,
        num_warps=warps,
        num_stages=2,
    )

    return Y
'''
        return {"code": textwrap.dedent(code).lstrip()}