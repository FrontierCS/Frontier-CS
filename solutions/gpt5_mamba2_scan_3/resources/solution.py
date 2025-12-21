import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def _ceil_div(a, b):
    return (a + b - 1) // b

@triton.jit
def _kernel_params(X_ptr, A_ptr, B_ptr, P_ptr, Q_ptr, L, D,
                   stride_x_l, stride_x_d,
                   stride_a_l, stride_a_d,
                   stride_b_l, stride_b_d,
                   stride_p_c, stride_p_d,
                   stride_q_c, stride_q_d,
                   CH: tl.constexpr, BD: tl.constexpr):
    pid_d = tl.program_id(0)
    pid_c = tl.program_id(1)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    l0 = pid_c * CH

    p = tl.full([BD], 1.0, tl.float32)
    s = tl.full([BD], 0.0, tl.float32)

    for t in range(CH):
        l = l0 + t
        a = tl.load(A_ptr + l * stride_a_l + offs_d * stride_a_d, mask=mask_d, other=1.0)
        b = tl.load(B_ptr + l * stride_b_l + offs_d * stride_b_d, mask=mask_d, other=0.0)
        x = tl.load(X_ptr + l * stride_x_l + offs_d * stride_x_d, mask=mask_d, other=0.0)
        a = a.to(tl.float32)
        b = b.to(tl.float32)
        x = x.to(tl.float32)
        s = a * s + b * x
        p = p * a

    tl.store(P_ptr + pid_c * stride_p_c + offs_d * stride_p_d, p, mask=mask_d)
    tl.store(Q_ptr + pid_c * stride_q_c + offs_d * stride_q_d, s, mask=mask_d)

@triton.jit
def _kernel_prefix(P_ptr, Q_ptr, S_ptr, D,
                   stride_p_c, stride_p_d,
                   stride_q_c, stride_q_d,
                   stride_s_c, stride_s_d,
                   C: tl.constexpr, BD: tl.constexpr):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    s = tl.full([BD], 0.0, tl.float32)
    for c in range(C):
        tl.store(S_ptr + c * stride_s_c + offs_d * stride_s_d, s, mask=mask_d)
        p = tl.load(P_ptr + c * stride_p_c + offs_d * stride_p_d, mask=mask_d, other=1.0).to(tl.float32)
        q = tl.load(Q_ptr + c * stride_q_c + offs_d * stride_q_d, mask=mask_d, other=0.0).to(tl.float32)
        s = p * s + q

@triton.jit
def _kernel_out(X_ptr, A_ptr, B_ptr, S_ptr, Y_ptr, L, D,
                stride_x_l, stride_x_d,
                stride_a_l, stride_a_d,
                stride_b_l, stride_b_d,
                stride_s_c, stride_s_d,
                stride_y_l, stride_y_d,
                CH: tl.constexpr, BD: tl.constexpr):
    pid_d = tl.program_id(0)
    pid_c = tl.program_id(1)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    l0 = pid_c * CH

    s = tl.load(S_ptr + pid_c * stride_s_c + offs_d * stride_s_d, mask=mask_d, other=0.0).to(tl.float32)

    for t in range(CH):
        l = l0 + t
        a = tl.load(A_ptr + l * stride_a_l + offs_d * stride_a_d, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(B_ptr + l * stride_b_l + offs_d * stride_b_d, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + l * stride_x_l + offs_d * stride_x_d, mask=mask_d, other=0.0).to(tl.float32)
        s = a * s + b * x
        tl.store(Y_ptr + l * stride_y_l + offs_d * stride_y_d, s.to(tl.float16), mask=mask_d)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        raise ValueError("All tensors must be CUDA tensors.")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise ValueError("All tensors must be float16.")
    if X.shape != A.shape or X.shape != B.shape:
        raise ValueError("X, A, B must have the same shape.")
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk.")
    C = L // chunk

    if not X.is_contiguous():
        X = X.contiguous()
    if not A.is_contiguous():
        A = A.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    P = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Q = torch.empty((C, D), device=X.device, dtype=torch.float32)
    S_in = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    grid_cd = (_ceil_div(D, BD), C)
    num_warps = 4 if BD <= 128 else 8
    num_stages = 2

    _kernel_params[grid_cd](
        X, A, B, P, Q, L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        P.stride(0), P.stride(1),
        Q.stride(0), Q.stride(1),
        CH=chunk, BD=BD,
        num_warps=num_warps, num_stages=num_stages
    )

    grid_d = (_ceil_div(D, BD),)
    _kernel_prefix[grid_d](
        P, Q, S_in, D,
        P.stride(0), P.stride(1),
        Q.stride(0), Q.stride(1),
        S_in.stride(0), S_in.stride(1),
        C=C, BD=BD,
        num_warps=num_warps, num_stages=num_stages
    )

    _kernel_out[grid_cd](
        X, A, B, S_in, Y, L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        S_in.stride(0), S_in.stride(1),
        Y.stride(0), Y.stride(1),
        CH=chunk, BD=BD,
        num_warps=num_warps, num_stages=num_stages
    )

    return Y
"""
        return {"code": code}
