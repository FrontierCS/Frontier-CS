import textwrap


KERNEL_CODE = textwrap.dedent(
    r"""
import math
import torch
import triton
import triton.language as tl

_BUFFER_CACHE = {}

def _get_buffers(device, nchunks: int, D: int):
    key = (device.index, nchunks, D)
    bufs = _BUFFER_CACHE.get(key, None)
    if bufs is None or any((b is None) or (not b.is_cuda) or (b.device != device) or (b.numel() != nchunks * D) for b in bufs):
        P = torch.empty((nchunks, D), device=device, dtype=torch.float32)
        Q = torch.empty((nchunks, D), device=device, dtype=torch.float32)
        S = torch.empty((nchunks, D), device=device, dtype=torch.float32)
        _BUFFER_CACHE[key] = (P, Q, S)
        return P, Q, S
    return bufs

@triton.jit
def _pq_kernel(
    X_ptr, A_ptr, B_ptr,
    P_ptr, Q_ptr,
    stride_xm: tl.constexpr, stride_xd: tl.constexpr,
    stride_am: tl.constexpr, stride_ad: tl.constexpr,
    stride_bm: tl.constexpr, stride_bd: tl.constexpr,
    stride_pqm: tl.constexpr, stride_pqd: tl.constexpr,
    D: tl.constexpr,
    chunk: tl.constexpr, BD: tl.constexpr,
):
    pid_m = tl.program_id(0)  # chunk id
    pid_n = tl.program_id(1)  # D-tile id

    offs_d = pid_n * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    y = tl.zeros([BD], dtype=tl.float32)
    p = tl.full([BD], 1.0, tl.float32)

    base_m = pid_m * chunk

    tl.multiple_of(offs_d, 8)

    for r in tl.static_range(0, chunk):
        m = base_m + r
        x = tl.load(X_ptr + m * stride_xm + offs_d * stride_xd, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + m * stride_am + offs_d * stride_ad, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + m * stride_bm + offs_d * stride_bd, mask=mask_d, other=0.0).to(tl.float32)
        y = a * y + b * x
        p = p * a

    tl.store(P_ptr + pid_m * stride_pqm + offs_d * stride_pqd, p, mask=mask_d)
    tl.store(Q_ptr + pid_m * stride_pqm + offs_d * stride_pqd, y, mask=mask_d)

@triton.jit
def _prefix_kernel(
    P_ptr, Q_ptr, S_ptr,
    stride_pqm: tl.constexpr, stride_pqd: tl.constexpr,
    stride_sm: tl.constexpr, stride_sd: tl.constexpr,
    nchunks: tl.constexpr,
    D: tl.constexpr,
    BD: tl.constexpr,
):
    pid_n = tl.program_id(0)  # D-tile id
    offs_d = pid_n * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    y = tl.zeros([BD], dtype=tl.float32)

    tl.multiple_of(offs_d, 8)

    for k in tl.static_range(0, nchunks):
        tl.store(S_ptr + k * stride_sm + offs_d * stride_sd, y, mask=mask_d)
        p = tl.load(P_ptr + k * stride_pqm + offs_d * stride_pqd, mask=mask_d, other=1.0)
        q = tl.load(Q_ptr + k * stride_pqm + offs_d * stride_pqd, mask=mask_d, other=0.0)
        y = p * y + q

@triton.jit
def _out_kernel(
    X_ptr, A_ptr, B_ptr,
    S_ptr, Y_ptr,
    stride_xm: tl.constexpr, stride_xd: tl.constexpr,
    stride_am: tl.constexpr, stride_ad: tl.constexpr,
    stride_bm: tl.constexpr, stride_bd: tl.constexpr,
    stride_sm: tl.constexpr, stride_sd: tl.constexpr,
    stride_ym: tl.constexpr, stride_yd: tl.constexpr,
    D: tl.constexpr,
    chunk: tl.constexpr, BD: tl.constexpr,
):
    pid_m = tl.program_id(0)  # chunk id
    pid_n = tl.program_id(1)  # D-tile id

    offs_d = pid_n * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    y = tl.load(S_ptr + pid_m * stride_sm + offs_d * stride_sd, mask=mask_d, other=0.0).to(tl.float32)

    base_m = pid_m * chunk

    tl.multiple_of(offs_d, 8)

    for r in tl.static_range(0, chunk):
        m = base_m + r
        x = tl.load(X_ptr + m * stride_xm + offs_d * stride_xd, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + m * stride_am + offs_d * stride_ad, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + m * stride_bm + offs_d * stride_bd, mask=mask_d, other=0.0).to(tl.float32)
        y = a * y + b * x
        tl.store(Y_ptr + m * stride_ym + offs_d * stride_yd, y.to(tl.float16), mask=mask_d)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        L, D = X.shape
        y = torch.zeros((D,), device=X.device, dtype=torch.float32)
        out = torch.empty((L, D), device=X.device, dtype=torch.float16)
        for t in range(L):
            y = A[t].float() * y + B[t].float() * X[t].float()
            out[t] = y.half()
        return out

    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.ndim == 2 and A.ndim == 2 and B.ndim == 2
    L, D = X.shape
    assert A.shape == (L, D) and B.shape == (L, D)
    assert L % chunk == 0
    if not (X.is_contiguous() and A.is_contiguous() and B.is_contiguous()):
        X = X.contiguous()
        A = A.contiguous()
        B = B.contiguous()

    device = X.device
    nchunks = L // chunk

    P, Q, S = _get_buffers(device, nchunks, D)
    Y = torch.empty((L, D), device=device, dtype=torch.float16)

    grid_pq = (nchunks, triton.cdiv(D, BD))
    _pq_kernel[grid_pq](
        X, A, B, P, Q,
        stride_xm=X.stride(0), stride_xd=X.stride(1),
        stride_am=A.stride(0), stride_ad=A.stride(1),
        stride_bm=B.stride(0), stride_bd=B.stride(1),
        stride_pqm=P.stride(0), stride_pqd=P.stride(1),
        D=D, chunk=chunk, BD=BD,
        num_warps=4,
        num_stages=2,
    )

    grid_pref = (triton.cdiv(D, BD),)
    _prefix_kernel[grid_pref](
        P, Q, S,
        stride_pqm=P.stride(0), stride_pqd=P.stride(1),
        stride_sm=S.stride(0), stride_sd=S.stride(1),
        nchunks=nchunks, D=D, BD=BD,
        num_warps=4,
        num_stages=2,
    )

    grid_out = (nchunks, triton.cdiv(D, BD))
    _out_kernel[grid_out](
        X, A, B, S, Y,
        stride_xm=X.stride(0), stride_xd=X.stride(1),
        stride_am=A.stride(0), stride_ad=A.stride(1),
        stride_bm=B.stride(0), stride_bd=B.stride(1),
        stride_sm=S.stride(0), stride_sd=S.stride(1),
        stride_ym=Y.stride(0), stride_yd=Y.stride(1),
        D=D, chunk=chunk, BD=BD,
        num_warps=4,
        num_stages=2,
    )
    return Y
"""
).strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}