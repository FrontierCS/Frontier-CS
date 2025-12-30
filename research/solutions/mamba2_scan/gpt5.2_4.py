import os
import textwrap


KERNEL_CODE = textwrap.dedent(
    r"""
import torch
import triton
import triton.language as tl


@triton.jit
def _pq_kernel(
    X_ptr, A_ptr, B_ptr,
    P_ptr, Q_ptr,
    stride_x0, stride_x1,
    stride_a0, stride_a1,
    stride_b0, stride_b1,
    stride_p0, stride_p1,
    D: tl.constexpr,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d = pid_d * BD + tl.arange(0, BD)
    m = d < D

    y = tl.zeros([BD], dtype=tl.float32)
    prod = tl.full([BD], 1.0, dtype=tl.float32)

    base_t = pid_c * CHUNK
    for i in tl.static_range(0, CHUNK):
        t = base_t + i

        off_x = t * stride_x0 + d * stride_x1
        off_a = t * stride_a0 + d * stride_a1
        off_b = t * stride_b0 + d * stride_b1

        a = tl.load(A_ptr + off_a, mask=m, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + off_b, mask=m, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + off_x, mask=m, other=0.0).to(tl.float32)

        y = tl.math.fma(a, y, b * x)
        prod = prod * a

    off_pq = pid_c * stride_p0 + d * stride_p1
    tl.store(P_ptr + off_pq, prod, mask=m)
    tl.store(Q_ptr + off_pq, y, mask=m)


@triton.jit
def _state_kernel(
    P_ptr, Q_ptr,
    S_ptr,
    stride_p0, stride_p1,
    stride_s0, stride_s1,
    D: tl.constexpr,
    NCHUNKS: tl.constexpr,
    BD: tl.constexpr,
):
    pid_d = tl.program_id(0)

    d = pid_d * BD + tl.arange(0, BD)
    m = d < D

    s = tl.zeros([BD], dtype=tl.float32)
    for c in tl.static_range(0, NCHUNKS):
        off_s = c * stride_s0 + d * stride_s1
        tl.store(S_ptr + off_s, s, mask=m)

        off_pq = c * stride_p0 + d * stride_p1
        p = tl.load(P_ptr + off_pq, mask=m, other=0.0).to(tl.float32)
        q = tl.load(Q_ptr + off_pq, mask=m, other=0.0).to(tl.float32)

        s = tl.math.fma(p, s, q)


@triton.jit
def _out_kernel(
    X_ptr, A_ptr, B_ptr,
    S_ptr,
    Y_ptr,
    stride_x0, stride_x1,
    stride_a0, stride_a1,
    stride_b0, stride_b1,
    stride_s0, stride_s1,
    stride_y0, stride_y1,
    D: tl.constexpr,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d = pid_d * BD + tl.arange(0, BD)
    m = d < D

    off_s = pid_c * stride_s0 + d * stride_s1
    y = tl.load(S_ptr + off_s, mask=m, other=0.0).to(tl.float32)

    base_t = pid_c * CHUNK
    for i in tl.static_range(0, CHUNK):
        t = base_t + i

        off_x = t * stride_x0 + d * stride_x1
        off_a = t * stride_a0 + d * stride_a1
        off_b = t * stride_b0 + d * stride_b1
        off_y = t * stride_y0 + d * stride_y1

        a = tl.load(A_ptr + off_a, mask=m, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + off_b, mask=m, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + off_x, mask=m, other=0.0).to(tl.float32)

        y = tl.math.fma(a, y, b * x)
        tl.store(Y_ptr + off_y, y.to(tl.float16), mask=m)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        raise ValueError("X, A, B must be CUDA tensors")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise ValueError("X, A, B must be torch.float16")
    if X.ndim != 2 or A.ndim != 2 or B.ndim != 2:
        raise ValueError("X, A, B must be 2D tensors of shape (L, D)")
    if X.shape != A.shape or X.shape != B.shape:
        raise ValueError("X, A, B must have the same shape")

    if not X.is_contiguous():
        X = X.contiguous()
    if not A.is_contiguous():
        A = A.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk")

    nchunks = L // chunk
    nblocks_d = triton.cdiv(D, BD)

    P = torch.empty((nchunks, D), device=X.device, dtype=torch.float32)
    Q = torch.empty((nchunks, D), device=X.device, dtype=torch.float32)
    S = torch.empty((nchunks, D), device=X.device, dtype=torch.float32)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    stride_x0, stride_x1 = X.stride()
    stride_a0, stride_a1 = A.stride()
    stride_b0, stride_b1 = B.stride()
    stride_p0, stride_p1 = P.stride()
    stride_s0, stride_s1 = S.stride()
    stride_y0, stride_y1 = Y.stride()

    grid_pq = (nchunks, nblocks_d)
    _pq_kernel[grid_pq](
        X, A, B,
        P, Q,
        stride_x0, stride_x1,
        stride_a0, stride_a1,
        stride_b0, stride_b1,
        stride_p0, stride_p1,
        D=D,
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    grid_s = (nblocks_d,)
    _state_kernel[grid_s](
        P, Q,
        S,
        stride_p0, stride_p1,
        stride_s0, stride_s1,
        D=D,
        NCHUNKS=nchunks,
        BD=BD,
        num_warps=4,
        num_stages=1,
    )

    grid_out = (nchunks, nblocks_d)
    _out_kernel[grid_out](
        X, A, B,
        S,
        Y,
        stride_x0, stride_x1,
        stride_a0, stride_a1,
        stride_b0, stride_b1,
        stride_s0, stride_s1,
        stride_y0, stride_y1,
        D=D,
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    return Y
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}