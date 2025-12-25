import os
import math
from typing import Dict, Optional

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
        UE_ptr,
        L: tl.constexpr,
        D: tl.constexpr,
        stride_x0: tl.constexpr,
        stride_x1: tl.constexpr,
        stride_a0: tl.constexpr,
        stride_a1: tl.constexpr,
        stride_b0: tl.constexpr,
        stride_b1: tl.constexpr,
        stride_ap0: tl.constexpr,
        stride_ap1: tl.constexpr,
        stride_ue0: tl.constexpr,
        stride_ue1: tl.constexpr,
        CHUNK: tl.constexpr,
        BD: tl.constexpr,
    ):
        pid_c = tl.program_id(0)
        pid_db = tl.program_id(1)

        offs_d = pid_db * BD + tl.arange(0, BD)
        m_d = offs_d < D

        base_t = pid_c * CHUNK

        x_ptrs = X_ptr + base_t * stride_x0 + offs_d * stride_x1
        a_ptrs = A_ptr + base_t * stride_a0 + offs_d * stride_a1
        b_ptrs = B_ptr + base_t * stride_b0 + offs_d * stride_b1

        y = tl.zeros([BD], dtype=tl.float32)
        ap = tl.full([BD], 1.0, dtype=tl.float32)

        # L divisible by CHUNK, so time indices valid; still guard D via m_d.
        for _ in range(CHUNK):
            x = tl.load(x_ptrs, mask=m_d, other=0.0).to(tl.float32)
            a = tl.load(a_ptrs, mask=m_d, other=0.0).to(tl.float32)
            b = tl.load(b_ptrs, mask=m_d, other=0.0).to(tl.float32)
            y = tl.math.fma(a, y, b * x)
            ap = ap * a
            x_ptrs += stride_x0
            a_ptrs += stride_a0
            b_ptrs += stride_b0

        ap_out_ptrs = AP_ptr + pid_c * stride_ap0 + offs_d * stride_ap1
        ue_out_ptrs = UE_ptr + pid_c * stride_ue0 + offs_d * stride_ue1
        tl.store(ap_out_ptrs, ap, mask=m_d)
        tl.store(ue_out_ptrs, y, mask=m_d)

    @triton.jit
    def _chunk_init_kernel(
        AP_ptr,
        UE_ptr,
        INIT_ptr,
        C: tl.constexpr,
        D: tl.constexpr,
        stride_ap0: tl.constexpr,
        stride_ap1: tl.constexpr,
        stride_ue0: tl.constexpr,
        stride_ue1: tl.constexpr,
        stride_i0: tl.constexpr,
        stride_i1: tl.constexpr,
        BD: tl.constexpr,
    ):
        pid_db = tl.program_id(0)
        offs_d = pid_db * BD + tl.arange(0, BD)
        m_d = offs_d < D

        state = tl.zeros([BD], dtype=tl.float32)

        ap_ptrs = AP_ptr + offs_d * stride_ap1
        ue_ptrs = UE_ptr + offs_d * stride_ue1
        i_ptrs = INIT_ptr + offs_d * stride_i1

        for _ in range(C):
            tl.store(i_ptrs, state, mask=m_d)
            ap = tl.load(ap_ptrs, mask=m_d, other=0.0).to(tl.float32)
            ue = tl.load(ue_ptrs, mask=m_d, other=0.0).to(tl.float32)
            state = tl.math.fma(ap, state, ue)
            ap_ptrs += stride_ap0
            ue_ptrs += stride_ue0
            i_ptrs += stride_i0

    @triton.jit
    def _chunk_compute_kernel(
        X_ptr,
        A_ptr,
        B_ptr,
        INIT_ptr,
        Y_ptr,
        L: tl.constexpr,
        D: tl.constexpr,
        stride_x0: tl.constexpr,
        stride_x1: tl.constexpr,
        stride_a0: tl.constexpr,
        stride_a1: tl.constexpr,
        stride_b0: tl.constexpr,
        stride_b1: tl.constexpr,
        stride_i0: tl.constexpr,
        stride_i1: tl.constexpr,
        stride_y0: tl.constexpr,
        stride_y1: tl.constexpr,
        CHUNK: tl.constexpr,
        BD: tl.constexpr,
    ):
        pid_c = tl.program_id(0)
        pid_db = tl.program_id(1)

        offs_d = pid_db * BD + tl.arange(0, BD)
        m_d = offs_d < D

        init_ptrs = INIT_ptr + pid_c * stride_i0 + offs_d * stride_i1
        y = tl.load(init_ptrs, mask=m_d, other=0.0).to(tl.float32)

        base_t = pid_c * CHUNK
        x_ptrs = X_ptr + base_t * stride_x0 + offs_d * stride_x1
        a_ptrs = A_ptr + base_t * stride_a0 + offs_d * stride_a1
        b_ptrs = B_ptr + base_t * stride_b0 + offs_d * stride_b1
        y_ptrs = Y_ptr + base_t * stride_y0 + offs_d * stride_y1

        for _ in range(CHUNK):
            x = tl.load(x_ptrs, mask=m_d, other=0.0).to(tl.float32)
            a = tl.load(a_ptrs, mask=m_d, other=0.0).to(tl.float32)
            b = tl.load(b_ptrs, mask=m_d, other=0.0).to(tl.float32)
            y = tl.math.fma(a, y, b * x)
            tl.store(y_ptrs, y.to(tl.float16), mask=m_d)
            x_ptrs += stride_x0
            a_ptrs += stride_a0
            b_ptrs += stride_b0
            y_ptrs += stride_y0


_intermediate_cache = {}


def _get_intermediates(device: torch.device, C: int, D: int):
    key = (device.type, device.index, C, D)
    v = _intermediate_cache.get(key, None)
    if v is None:
        AP = torch.empty((C, D), device=device, dtype=torch.float32)
        UE = torch.empty((C, D), device=device, dtype=torch.float32)
        INIT = torch.empty((C, D), device=device, dtype=torch.float32)
        _intermediate_cache[key] = (AP, UE, INIT)
        return AP, UE, INIT
    AP, UE, INIT = v
    if (AP.device != device) or (AP.shape != (C, D)):
        AP = torch.empty((C, D), device=device, dtype=torch.float32)
        UE = torch.empty((C, D), device=device, dtype=torch.float32)
        INIT = torch.empty((C, D), device=device, dtype=torch.float32)
        _intermediate_cache[key] = (AP, UE, INIT)
    return _intermediate_cache[key]


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if triton is None:
        # Fallback (slow): for environments without triton.
        L, D = X.shape
        y = torch.zeros((D,), device=X.device, dtype=torch.float32)
        Y = torch.empty((L, D), device=X.device, dtype=torch.float16)
        for t in range(L):
            y = A[t].float() * y + (B[t].float() * X[t].float())
            Y[t] = y.half()
        return Y

    assert X.is_cuda and A.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.ndim == 2 and A.ndim == 2 and B.ndim == 2
    L, D = X.shape
    assert A.shape == (L, D) and B.shape == (L, D)
    assert L % chunk == 0

    C = L // chunk
    AP, UE, INIT = _get_intermediates(X.device, C, D)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    sx0, sx1 = X.stride(0), X.stride(1)
    sa0, sa1 = A.stride(0), A.stride(1)
    sb0, sb1 = B.stride(0), B.stride(1)
    sy0, sy1 = Y.stride(0), Y.stride(1)

    sap0, sap1 = AP.stride(0), AP.stride(1)
    sue0, sue1 = UE.stride(0), UE.stride(1)
    si0, si1 = INIT.stride(0), INIT.stride(1)

    nD = (D + BD - 1) // BD

    num_warps = 4 if BD >= 128 else 2
    num_stages = 2

    grid_summary = (C, nD)
    _chunk_summary_kernel[grid_summary](
        X, A, B, AP, UE,
        L=L, D=D,
        stride_x0=sx0, stride_x1=sx1,
        stride_a0=sa0, stride_a1=sa1,
        stride_b0=sb0, stride_b1=sb1,
        stride_ap0=sap0, stride_ap1=sap1,
        stride_ue0=sue0, stride_ue1=sue1,
        CHUNK=chunk, BD=BD,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    grid_init = (nD,)
    _chunk_init_kernel[grid_init](
        AP, UE, INIT,
        C=C, D=D,
        stride_ap0=sap0, stride_ap1=sap1,
        stride_ue0=sue0, stride_ue1=sue1,
        stride_i0=si0, stride_i1=si1,
        BD=BD,
        num_warps=2 if BD <= 128 else 4,
        num_stages=1,
    )

    grid_compute = (C, nD)
    _chunk_compute_kernel[grid_compute](
        X, A, B, INIT, Y,
        L=L, D=D,
        stride_x0=sx0, stride_x1=sx1,
        stride_a0=sa0, stride_a1=sa1,
        stride_b0=sb0, stride_b1=sb1,
        stride_i0=si0, stride_i1=si1,
        stride_y0=sy0, stride_y1=sy1,
        CHUNK=chunk, BD=BD,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"program_path": os.path.abspath(__file__)}