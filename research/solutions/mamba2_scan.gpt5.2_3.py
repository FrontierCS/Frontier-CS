import textwrap

KERNEL_CODE = textwrap.dedent(
    r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_params_kernel(X_ptr, A_ptr, B_ptr, P_ptr, Q_ptr,
                         stride_x0: tl.constexpr, stride_x1: tl.constexpr,
                         stride_a0: tl.constexpr, stride_a1: tl.constexpr,
                         stride_b0: tl.constexpr, stride_b1: tl.constexpr,
                         D: tl.constexpr, CHUNK: tl.constexpr, BD: tl.constexpr):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    p = tl.full([BD], 1.0, tl.float32)
    q = tl.zeros([BD], tl.float32)

    t0 = pid_c * CHUNK
    base_x = t0 * stride_x0 + offs_d * stride_x1
    base_a = t0 * stride_a0 + offs_d * stride_a1
    base_b = t0 * stride_b0 + offs_d * stride_b1

    for i in range(CHUNK):
        x = tl.load(X_ptr + base_x + i * stride_x0, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + base_a + i * stride_a0, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(B_ptr + base_b + i * stride_b0, mask=mask_d, other=0.0).to(tl.float32)
        u = b * x
        q = a * q + u
        p = a * p

    out = pid_c * D + offs_d
    tl.store(P_ptr + out, p, mask=mask_d)
    tl.store(Q_ptr + out, q, mask=mask_d)


@triton.jit
def _scan_chunks_kernel(P_ptr, Q_ptr, Yin_ptr,
                        D: tl.constexpr, C: tl.constexpr, BD: tl.constexpr):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    y = tl.zeros([BD], tl.float32)
    for c in range(C):
        tl.store(Yin_ptr + c * D + offs_d, y, mask=mask_d)
        p = tl.load(P_ptr + c * D + offs_d, mask=mask_d, other=1.0).to(tl.float32)
        q = tl.load(Q_ptr + c * D + offs_d, mask=mask_d, other=0.0).to(tl.float32)
        y = p * y + q


@triton.jit
def _compute_y_kernel(X_ptr, A_ptr, B_ptr, Yin_ptr, Y_ptr,
                      stride_x0: tl.constexpr, stride_x1: tl.constexpr,
                      stride_a0: tl.constexpr, stride_a1: tl.constexpr,
                      stride_b0: tl.constexpr, stride_b1: tl.constexpr,
                      stride_y0: tl.constexpr, stride_y1: tl.constexpr,
                      D: tl.constexpr, CHUNK: tl.constexpr, BD: tl.constexpr):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    y = tl.load(Yin_ptr + pid_c * D + offs_d, mask=mask_d, other=0.0).to(tl.float32)

    t0 = pid_c * CHUNK
    base_x = t0 * stride_x0 + offs_d * stride_x1
    base_a = t0 * stride_a0 + offs_d * stride_a1
    base_b = t0 * stride_b0 + offs_d * stride_b1
    base_y = t0 * stride_y0 + offs_d * stride_y1

    for i in range(CHUNK):
        x = tl.load(X_ptr + base_x + i * stride_x0, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + base_a + i * stride_a0, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(B_ptr + base_b + i * stride_b0, mask=mask_d, other=0.0).to(tl.float32)
        y = a * y + b * x
        tl.store(Y_ptr + base_y + i * stride_y0, y.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        raise ValueError("X, A, B must be CUDA tensors")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise ValueError("X, A, B must be float16")
    if X.ndim != 2 or A.ndim != 2 or B.ndim != 2:
        raise ValueError("X, A, B must be 2D tensors of shape (L, D)")
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
    C = L // chunk

    if D % 64 == 0:
        BD0 = 64
    else:
        BD0 = min(BD, 128)

    if BD0 <= 64:
        num_warps = 4
    else:
        num_warps = 8

    P = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Q = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Yin = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    grid_c = (C, triton.cdiv(D, BD0))
    _chunk_params_kernel[grid_c](
        X, A, B, P, Q,
        stride_x0=X.stride(0), stride_x1=X.stride(1),
        stride_a0=A.stride(0), stride_a1=A.stride(1),
        stride_b0=B.stride(0), stride_b1=B.stride(1),
        D=D, CHUNK=chunk, BD=BD0,
        num_warps=num_warps, num_stages=2
    )

    grid_s = (triton.cdiv(D, BD0),)
    _scan_chunks_kernel[grid_s](
        P, Q, Yin,
        D=D, C=C, BD=BD0,
        num_warps=1, num_stages=1
    )

    _compute_y_kernel[grid_c](
        X, A, B, Yin, Y,
        stride_x0=X.stride(0), stride_x1=X.stride(1),
        stride_a0=A.stride(0), stride_a1=A.stride(1),
        stride_b0=B.stride(0), stride_b1=B.stride(1),
        stride_y0=Y.stride(0), stride_y1=Y.stride(1),
        D=D, CHUNK=chunk, BD=BD0,
        num_warps=num_warps, num_stages=2
    )

    return Y
'''
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}