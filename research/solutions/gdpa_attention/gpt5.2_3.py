import os
import math
from typing import Optional, Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_gqz: tl.constexpr, stride_gqh: tl.constexpr, stride_gqm: tl.constexpr, stride_gqd: tl.constexpr,
    stride_gkz: tl.constexpr, stride_gkh: tl.constexpr, stride_gkn: tl.constexpr, stride_gkd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    sm_scale: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr,
    M: tl.constexpr, N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_h = tl.program_id(axis=1)
    pid_z = tl.program_id(axis=2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    q_base = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
    gq_base = GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh
    k_base = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    gk_base = GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh
    v_base = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    o_base = O_ptr + pid_z * stride_oz + pid_h * stride_oh

    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = gq_base + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd
    q_mask = (offs_m[:, None] < M) & (offs_d[None, :] < D)

    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    qg = q * tl.sigmoid(gq)
    qg = qg.to(tl.float16)

    m_i = tl.full([BLOCK_M], -1.0e9, tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = gk_base + offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkd
        kv_mask = n_mask[:, None] & (offs_d[None, :] < D)

        k = tl.load(k_ptrs, mask=kv_mask, other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=kv_mask, other=0.0).to(tl.float32)
        kg = (k * tl.sigmoid(gk)).to(tl.float16)

        qk = tl.dot(qg, tl.trans(kg)).to(tl.float32)
        qk = qk * sm_scale
        qk = tl.where(n_mask[None, :], qk, -1.0e9)

        m_ij = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)

        p = tl.exp(qk - m_i_new[:, None])
        l_ij = tl.sum(p, axis=1)

        l_i = l_i * alpha + l_ij

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v_mask = n_mask[:, None] & (offs_dv[None, :] < DV)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float16)

        p16 = p.to(tl.float16)
        acc = acc * alpha[:, None] + tl.dot(p16, v)

        m_i = m_i_new

    out = acc / l_i[:, None]
    out = out.to(tl.float16)

    o_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = (offs_m[:, None] < M) & (offs_dv[None, :] < DV)
    tl.store(o_ptrs, out, mask=o_mask)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4
    Z, H, M, D = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Hk == H and Dk == D
    assert Zv == Z and Hv == H and Nv == N
    assert GQ.shape == Q.shape
    assert GK.shape == K.shape
    assert N == M

    if D <= 64:
        BLOCK_D = 64
    elif D <= 128:
        BLOCK_D = 128
    else:
        raise ValueError(f"Unsupported D={D}")

    if DV <= 64:
        BLOCK_DV = 64
    elif DV <= 128:
        BLOCK_DV = 128
    else:
        raise ValueError(f"Unsupported DV={DV}")

    BLOCK_M = 128
    BLOCK_N = 64
    num_warps = 4
    num_stages = 3

    o = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    sm_scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M), H, Z)

    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, o,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        o.stride(0), o.stride(1), o.stride(2), o.stride(3),
        sm_scale=sm_scale,
        Z=Z, H=H,
        M=M, N=N, D=D, DV=DV,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return o
'''
        return {"code": code}