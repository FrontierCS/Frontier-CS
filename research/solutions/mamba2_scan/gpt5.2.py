import os
import inspect
import textwrap
from typing import Optional, Dict

import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_pq_kernel(
    X_ptr, A_ptr, B_ptr,
    P_ptr, Q_ptr,
    D: tl.constexpr,
    sx0: tl.constexpr, sx1: tl.constexpr,
    sa0: tl.constexpr, sa1: tl.constexpr,
    sb0: tl.constexpr, sb1: tl.constexpr,
    sp0: tl.constexpr, sp1: tl.constexpr,
    sq0: tl.constexpr, sq1: tl.constexpr,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_db = tl.program_id(1)

    d = pid_db * BD + tl.arange(0, BD)
    mask_d = d < D

    row0 = pid_chunk * CHUNK

    x_ptr = X_ptr + row0 * sx0 + d * sx1
    a_ptr = A_ptr + row0 * sa0 + d * sa1
    b_ptr = B_ptr + row0 * sb0 + d * sb1

    y = tl.zeros([BD], dtype=tl.float32)
    p = tl.full([BD], 1.0, dtype=tl.float32)

    for _ in tl.static_range(0, CHUNK):
        a = tl.load(a_ptr, mask=mask_d, other=0.0)
        x = tl.load(x_ptr, mask=mask_d, other=0.0)
        b = tl.load(b_ptr, mask=mask_d, other=0.0)
        a32 = tl.cast(a, tl.float32)
        u32 = tl.cast(x, tl.float32) * tl.cast(b, tl.float32)
        y = a32 * y + u32
        p = a32 * p
        x_ptr += sx0
        a_ptr += sa0
        b_ptr += sb0

    p_out_ptr = P_ptr + pid_chunk * sp0 + d * sp1
    q_out_ptr = Q_ptr + pid_chunk * sq0 + d * sq1
    tl.store(p_out_ptr, p, mask=mask_d)
    tl.store(q_out_ptr, y, mask=mask_d)


@triton.jit
def _chunk_prefix_kernel(
    P_ptr, Q_ptr, S_ptr,
    D: tl.constexpr,
    sp0: tl.constexpr, sp1: tl.constexpr,
    sq0: tl.constexpr, sq1: tl.constexpr,
    ss0: tl.constexpr, ss1: tl.constexpr,
    C: tl.constexpr, BD: tl.constexpr,
):
    pid_db = tl.program_id(0)
    d = pid_db * BD + tl.arange(0, BD)
    mask_d = d < D

    p_ptr = P_ptr + d * sp1
    q_ptr = Q_ptr + d * sq1
    s_ptr = S_ptr + d * ss1

    y = tl.zeros([BD], dtype=tl.float32)
    for _ in tl.static_range(0, C):
        tl.store(s_ptr, y, mask=mask_d)
        p = tl.load(p_ptr, mask=mask_d, other=0.0)
        q = tl.load(q_ptr, mask=mask_d, other=0.0)
        y = tl.cast(p, tl.float32) * y + tl.cast(q, tl.float32)
        p_ptr += sp0
        q_ptr += sq0
        s_ptr += ss0


@triton.jit
def _chunk_out_kernel(
    X_ptr, A_ptr, B_ptr,
    S_ptr, Y_ptr,
    D: tl.constexpr,
    sx0: tl.constexpr, sx1: tl.constexpr,
    sa0: tl.constexpr, sa1: tl.constexpr,
    sb0: tl.constexpr, sb1: tl.constexpr,
    ss0: tl.constexpr, ss1: tl.constexpr,
    sy0: tl.constexpr, sy1: tl.constexpr,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_db = tl.program_id(1)

    d = pid_db * BD + tl.arange(0, BD)
    mask_d = d < D

    row0 = pid_chunk * CHUNK

    s_ptr = S_ptr + pid_chunk * ss0 + d * ss1
    y = tl.load(s_ptr, mask=mask_d, other=0.0)
    y = tl.cast(y, tl.float32)

    x_ptr = X_ptr + row0 * sx0 + d * sx1
    a_ptr = A_ptr + row0 * sa0 + d * sa1
    b_ptr = B_ptr + row0 * sb0 + d * sb1
    y_ptr = Y_ptr + row0 * sy0 + d * sy1

    for _ in tl.static_range(0, CHUNK):
        a = tl.load(a_ptr, mask=mask_d, other=0.0)
        x = tl.load(x_ptr, mask=mask_d, other=0.0)
        b = tl.load(b_ptr, mask=mask_d, other=0.0)
        a32 = tl.cast(a, tl.float32)
        u32 = tl.cast(x, tl.float32) * tl.cast(b, tl.float32)
        y = a32 * y + u32
        tl.store(y_ptr, tl.cast(y, tl.float16), mask=mask_d)
        x_ptr += sx0
        a_ptr += sa0
        b_ptr += sb0
        y_ptr += sy0


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        L, D = X.shape
        y = torch.empty((L, D), device=X.device, dtype=torch.float32)
        prev = torch.zeros((D,), device=X.device, dtype=torch.float32)
        X32 = X.float()
        A32 = A.float()
        B32 = B.float()
        for t in range(L):
            prev = A32[t] * prev + B32[t] * X32[t]
            y[t] = prev
        return y.to(torch.float16)

    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.ndim == 2 and A.ndim == 2 and B.ndim == 2
    L, D = X.shape
    assert A.shape == (L, D) and B.shape == (L, D)
    assert L % chunk == 0

    C = L // chunk

    P = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Q = torch.empty((C, D), device=X.device, dtype=torch.float32)
    S = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    num_warps = 4 if BD <= 128 else 8
    num_stages = 2

    grid_pq = (C, triton.cdiv(D, BD))
    _chunk_pq_kernel[grid_pq](
        X, A, B,
        P, Q,
        D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        P.stride(0), P.stride(1),
        Q.stride(0), Q.stride(1),
        CHUNK=chunk, BD=BD,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    grid_prefix = (triton.cdiv(D, BD),)
    _chunk_prefix_kernel[grid_prefix](
        P, Q, S,
        D,
        P.stride(0), P.stride(1),
        Q.stride(0), Q.stride(1),
        S.stride(0), S.stride(1),
        C=C, BD=BD,
        num_warps=2,
        num_stages=1,
    )

    _chunk_out_kernel[grid_pq](
        X, A, B,
        S, Y,
        D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        S.stride(0), S.stride(1),
        Y.stride(0), Y.stride(1),
        CHUNK=chunk, BD=BD,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        path = globals().get("__file__", None)
        if path is not None and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return {"code": f.read()}
            except Exception:
                pass

        src_parts = []
        for obj in [
            _chunk_pq_kernel,
            _chunk_prefix_kernel,
            _chunk_out_kernel,
            chunk_scan,
            Solution,
        ]:
            try:
                src_parts.append(inspect.getsource(obj))
            except Exception:
                pass
        code = "\n\n".join([
            "import os\nimport inspect\nimport textwrap\nfrom typing import Optional, Dict\n\nimport torch\nimport triton\nimport triton.language as tl\n",
            *src_parts
        ])
        return {"code": code}