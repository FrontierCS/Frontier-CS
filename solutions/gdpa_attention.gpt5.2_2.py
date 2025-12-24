import math
from typing import Dict, Optional


KERNEL_CODE = r'''
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
    Z: tl.constexpr, H: tl.constexpr,
    M: tl.constexpr, N: tl.constexpr,
    DQ: tl.constexpr, DV: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh - z * H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, DQ)
    offs_dv = tl.arange(0, DV)

    q_base = Q_ptr + z * stride_qz + h * stride_qh
    gq_base = GQ_ptr + z * stride_gqz + h * stride_gqh

    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = gq_base + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd

    m_mask = offs_m < M
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
    qg = (q * tl.sigmoid(gq)).to(tl.float16)

    m_i = tl.full([BLOCK_M], -float("inf"), tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, DV], dtype=tl.float32)

    k_base = K_ptr + z * stride_kz + h * stride_kh
    gk_base = GK_ptr + z * stride_gkz + h * stride_gkh
    v_base = V_ptr + z * stride_vz + h * stride_vh

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = k_base + offs_n[None, :] * stride_kn + offs_dq[:, None] * stride_kd
        gk_ptrs = gk_base + offs_n[None, :] * stride_gkn + offs_dq[:, None] * stride_gkd

        k = tl.load(k_ptrs, mask=n_mask[None, :], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=n_mask[None, :], other=0.0).to(tl.float32)
        kg = (k * tl.sigmoid(gk)).to(tl.float16)

        qk = tl.dot(qg, kg).to(tl.float32) * SCALE
        qk = tl.where(n_mask[None, :], qk, -1.0e9)

        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)

        p = tl.exp(qk - m_new[:, None])
        l_new = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

        p16 = p.to(tl.float16)
        acc = acc * alpha[:, None] + tl.dot(p16, v).to(tl.float32)

        m_i = m_new
        l_i = l_new

    l_i = tl.maximum(l_i, 1.0e-6)
    out = (acc / l_i[:, None]).to(tl.float16)

    o_base = O_ptr + z * stride_oz + h * stride_oh
    o_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=m_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda):
        DQ = Q.shape[-1]
        scale = 1.0 / math.sqrt(DQ)
        Qg = (Q * torch.sigmoid(GQ)).float()
        Kg = (K * torch.sigmoid(GK)).float()
        scores = torch.matmul(Qg, Kg.transpose(-1, -2)) * scale
        attn = torch.softmax(scores, dim=-1).to(dtype=V.dtype)
        out = torch.matmul(attn, V)
        return out

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Hk == H and N == M and DQk == DQ
    assert Zv == Z and Hv == H and Nv == N
    assert GQ.shape == Q.shape
    assert GK.shape == K.shape

    out = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64
    num_warps = 4
    num_stages = 3

    scale = 1.0 / math.sqrt(DQ)

    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z=Z, H=H,
        M=M, N=N,
        DQ=DQ, DV=DV,
        SCALE=scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return out
'''


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"code": KERNEL_CODE}
