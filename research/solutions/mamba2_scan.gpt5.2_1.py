import os
import math
import functools
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.jit
    def _chunk_summary_kernel(
        X_ptr,
        A_ptr,
        B_ptr,
        AP_ptr,
        U_ptr,
        D: tl.constexpr,
        stride_x0: tl.constexpr,
        stride_x1: tl.constexpr,
        stride_a0: tl.constexpr,
        stride_a1: tl.constexpr,
        stride_b0: tl.constexpr,
        stride_b1: tl.constexpr,
        stride_ap0: tl.constexpr,
        stride_ap1: tl.constexpr,
        stride_u0: tl.constexpr,
        stride_u1: tl.constexpr,
        CHUNK: tl.constexpr,
        BD: tl.constexpr,
    ):
        pid_c = tl.program_id(0)
        pid_d = tl.program_id(1)
        d = pid_d * BD + tl.arange(0, BD)
        mask_d = d < D

        t0 = pid_c * CHUNK
        x_base = X_ptr + t0 * stride_x0 + d * stride_x1
        a_base = A_ptr + t0 * stride_a0 + d * stride_a1
        b_base = B_ptr + t0 * stride_b0 + d * stride_b1

        y = tl.zeros((BD,), dtype=tl.float32)
        ap = tl.full((BD,), 1.0, dtype=tl.float32)

        for i in range(0, CHUNK):
            x = tl.load(x_base + i * stride_x0, mask=mask_d, other=0.0).to(tl.float32)
            a = tl.load(a_base + i * stride_a0, mask=mask_d, other=0.0).to(tl.float32)
            b = tl.load(b_base + i * stride_b0, mask=mask_d, other=0.0).to(tl.float32)
            y = a * y + b * x
            ap = a * ap

        ap_out = AP_ptr + pid_c * stride_ap0 + d * stride_ap1
        u_out = U_ptr + pid_c * stride_u0 + d * stride_u1
        tl.store(ap_out, ap, mask=mask_d)
        tl.store(u_out, y, mask=mask_d)

    @triton.jit
    def _chunk_state_scan_kernel(
        AP_ptr,
        U_ptr,
        S_ptr,
        D: tl.constexpr,
        stride_ap0: tl.constexpr,
        stride_ap1: tl.constexpr,
        stride_u0: tl.constexpr,
        stride_u1: tl.constexpr,
        stride_s0: tl.constexpr,
        stride_s1: tl.constexpr,
        NCHUNKS: tl.constexpr,
        BD: tl.constexpr,
    ):
        pid_d = tl.program_id(0)
        d = pid_d * BD + tl.arange(0, BD)
        mask_d = d < D

        y = tl.zeros((BD,), dtype=tl.float32)

        for c in range(0, NCHUNKS):
            s_out = S_ptr + c * stride_s0 + d * stride_s1
            tl.store(s_out, y, mask=mask_d)

            ap = tl.load(AP_ptr + c * stride_ap0 + d * stride_ap1, mask=mask_d, other=1.0).to(tl.float32)
            u = tl.load(U_ptr + c * stride_u0 + d * stride_u1, mask=mask_d, other=0.0).to(tl.float32)
            y = ap * y + u

    @triton.jit
    def _chunk_apply_kernel(
        X_ptr,
        A_ptr,
        B_ptr,
        S_ptr,
        Y_ptr,
        D: tl.constexpr,
        stride_x0: tl.constexpr,
        stride_x1: tl.constexpr,
        stride_a0: tl.constexpr,
        stride_a1: tl.constexpr,
        stride_b0: tl.constexpr,
        stride_b1: tl.constexpr,
        stride_s0: tl.constexpr,
        stride_s1: tl.constexpr,
        stride_y0: tl.constexpr,
        stride_y1: tl.constexpr,
        CHUNK: tl.constexpr,
        BD: tl.constexpr,
    ):
        pid_c = tl.program_id(0)
        pid_d = tl.program_id(1)
        d = pid_d * BD + tl.arange(0, BD)
        mask_d = d < D

        t0 = pid_c * CHUNK

        y = tl.load(S_ptr + pid_c * stride_s0 + d * stride_s1, mask=mask_d, other=0.0).to(tl.float32)

        x_base = X_ptr + t0 * stride_x0 + d * stride_x1
        a_base = A_ptr + t0 * stride_a0 + d * stride_a1
        b_base = B_ptr + t0 * stride_b0 + d * stride_b1
        y_base = Y_ptr + t0 * stride_y0 + d * stride_y1

        for i in range(0, CHUNK):
            x = tl.load(x_base + i * stride_x0, mask=mask_d, other=0.0).to(tl.float32)
            a = tl.load(a_base + i * stride_a0, mask=mask_d, other=0.0).to(tl.float32)
            b = tl.load(b_base + i * stride_b0, mask=mask_d, other=0.0).to(tl.float32)
            y = a * y + b * x
            tl.store(y_base + i * stride_y0, y.to(tl.float16), mask=mask_d)


_tmp_cache = {}


def _get_tmp(device, n_chunks, D):
    key = (int(device.index) if device.type == "cuda" else -1, n_chunks, D)
    v = _tmp_cache.get(key, None)
    if v is not None:
        AP, U, S = v
        if AP.device == device and AP.shape == (n_chunks, D) and AP.dtype == torch.float32:
            return AP, U, S
    AP = torch.empty((n_chunks, D), device=device, dtype=torch.float32)
    U = torch.empty((n_chunks, D), device=device, dtype=torch.float32)
    S = torch.empty((n_chunks, D), device=device, dtype=torch.float32)
    _tmp_cache[key] = (AP, U, S)
    return AP, U, S


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (isinstance(X, torch.Tensor) and isinstance(A, torch.Tensor) and isinstance(B, torch.Tensor)):
        raise TypeError("X, A, B must be torch.Tensor")
    if X.ndim != 2 or A.ndim != 2 or B.ndim != 2:
        raise ValueError("X, A, B must be 2D tensors (L, D)")
    if X.shape != A.shape or X.shape != B.shape:
        raise ValueError("X, A, B must have the same shape (L, D)")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise ValueError("X, A, B must be torch.float16")
    if not X.is_cuda:
        L, D = X.shape
        y = torch.empty((L, D), device=X.device, dtype=torch.float16)
        yf = torch.zeros((D,), device=X.device, dtype=torch.float32)
        Xf = X.to(torch.float32)
        Af = A.to(torch.float32)
        Bf = B.to(torch.float32)
        for t in range(L):
            yf = Af[t] * yf + Bf[t] * Xf[t]
            y[t] = yf.to(torch.float16)
        return y
    if triton is None:
        raise RuntimeError("triton is not available")

    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk")
    n_chunks = L // chunk

    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    AP, U, S = _get_tmp(X.device, n_chunks, D)

    stride_x0, stride_x1 = X.stride(0), X.stride(1)
    stride_a0, stride_a1 = A.stride(0), A.stride(1)
    stride_b0, stride_b1 = B.stride(0), B.stride(1)
    stride_y0, stride_y1 = Y.stride(0), Y.stride(1)

    stride_ap0, stride_ap1 = AP.stride(0), AP.stride(1)
    stride_u0, stride_u1 = U.stride(0), U.stride(1)
    stride_s0, stride_s1 = S.stride(0), S.stride(1)

    grid1 = (n_chunks, triton.cdiv(D, BD))
    _chunk_summary_kernel[grid1](
        X,
        A,
        B,
        AP,
        U,
        D=D,
        stride_x0=stride_x0,
        stride_x1=stride_x1,
        stride_a0=stride_a0,
        stride_a1=stride_a1,
        stride_b0=stride_b0,
        stride_b1=stride_b1,
        stride_ap0=stride_ap0,
        stride_ap1=stride_ap1,
        stride_u0=stride_u0,
        stride_u1=stride_u1,
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    grid2 = (triton.cdiv(D, BD),)
    _chunk_state_scan_kernel[grid2](
        AP,
        U,
        S,
        D=D,
        stride_ap0=stride_ap0,
        stride_ap1=stride_ap1,
        stride_u0=stride_u0,
        stride_u1=stride_u1,
        stride_s0=stride_s0,
        stride_s1=stride_s1,
        NCHUNKS=n_chunks,
        BD=BD,
        num_warps=4,
        num_stages=1,
    )

    _chunk_apply_kernel[grid1](
        X,
        A,
        B,
        S,
        Y,
        D=D,
        stride_x0=stride_x0,
        stride_x1=stride_x1,
        stride_a0=stride_a0,
        stride_a1=stride_a1,
        stride_b0=stride_b0,
        stride_b1=stride_b1,
        stride_s0=stride_s0,
        stride_s1=stride_s1,
        stride_y0=stride_y0,
        stride_y1=stride_y1,
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except Exception:
            pass
        import inspect, sys
        return {"code": inspect.getsource(sys.modules[__name__])}