import textwrap

KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634

@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    sm_scale,
    H: tl.constexpr,
    M_CTX: tl.constexpr, N_CTX: tl.constexpr,
    D_HEAD: tl.constexpr, D_V: tl.constexpr,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    b = pid_bh // H
    h = pid_bh - b * H

    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    q_ptrs = Q_ptr + b * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(
        q_ptrs,
        mask=(offs_m[:, None] < M_CTX) & (offs_d[None, :] < D_HEAD),
        other=0.0,
        cache_modifier=".ca",
    ).to(tl.float16)

    m_i = tl.where(offs_m < M_CTX, -float("inf"), 0.0).to(tl.float32)
    l_i = tl.where(offs_m < M_CTX, 0.0, 1.0).to(tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)

        k_ptrs = K_ptr + b * stride_kz + h * stride_kh + offs_d[:, None] * stride_kd + offs_n[None, :] * stride_kn
        k = tl.load(
            k_ptrs,
            mask=(offs_d[:, None] < D_HEAD) & (offs_n[None, :] < N_CTX),
            other=0.0,
            cache_modifier=".cg",
        ).to(tl.float16)

        qk = tl.dot(q, k).to(tl.float32) * sm_scale

        mask = (offs_m[:, None] < M_CTX) & (offs_n[None, :] < N_CTX)
        if causal:
            mask = mask & (offs_n[None, :] <= offs_m[:, None])
        qk = tl.where(mask, qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        alpha = tl.exp2((m_i - m_ij) * _LOG2E)
        p = tl.exp2((qk - m_ij[:, None]) * _LOG2E)

        l_i = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = V_ptr + b * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(
            v_ptrs,
            mask=(offs_n[:, None] < N_CTX) & (offs_dv[None, :] < D_V),
            other=0.0,
            cache_modifier=".cg",
        ).to(tl.float16)

        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        m_i = m_ij

    out = acc / l_i[:, None]
    o_ptrs = O_ptr + b * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(
        o_ptrs,
        out.to(tl.float16),
        mask=(offs_m[:, None] < M_CTX) & (offs_dv[None, :] < D_V),
    )


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and Dq == Dk
    assert N == M
    assert Dq <= 64 and Dv <= 64

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    sm_scale = 1.0 / math.sqrt(Dq)

    if M >= 2048:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 8
        num_stages = 4
    else:
        BLOCK_M = 128
        BLOCK_N = 64
        num_warps = 4
        num_stages = 4

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    _flash_attn_fwd[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
        H=H,
        M_CTX=M, N_CTX=N,
        D_HEAD=Dq, D_V=Dv,
        causal=causal,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_D=64, BLOCK_DV=64,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
'''

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}