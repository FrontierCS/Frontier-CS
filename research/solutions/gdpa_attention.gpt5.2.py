import math
from typing import Optional, Dict


_KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    H: tl.constexpr,
    M_CTX,
    D_HEAD: tl.constexpr,
    D_V: tl.constexpr,
    N_CTX: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    z = pid_bh // H
    h = pid_bh - z * H

    q_bh_off = z * stride_qz + h * stride_qh
    k_bh_off = z * stride_kz + h * stride_kh
    v_bh_off = z * stride_vz + h * stride_vh
    gq_bh_off = z * stride_gqz + h * stride_gqh
    gk_bh_off = z * stride_gkz + h * stride_gkh
    o_bh_off = z * stride_oz + h * stride_oh

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M_CTX
    mask_d = offs_d < D_HEAD
    mask_dv = offs_dv < D_V

    q_ptrs = Q_ptr + q_bh_off + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ_ptr + gq_bh_off + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0).to(tl.float16)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0).to(tl.float16)

    gq_f = gq.to(tl.float32)
    # sigmoid
    gq_s = 1.0 / (1.0 + tl.exp(-gq_f))
    qg = (q.to(tl.float32) * gq_s) * SCALE
    qg = qg.to(tl.float16)

    m_i = tl.full((BLOCK_M,), -1.0e9, tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    LOG2E = 1.4426950408889634

    # Loop over K/V blocks
    for start_n in tl.static_range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        k_ptrs = K_ptr + k_bh_off + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = GK_ptr + gk_bh_off + offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0, eviction_policy="evict_last").to(tl.float16)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0, eviction_policy="evict_last").to(tl.float16)

        gk_f = gk.to(tl.float32)
        gk_s = 1.0 / (1.0 + tl.exp(-gk_f))
        kg = (k.to(tl.float32) * gk_s).to(tl.float16)

        # qk: [BLOCK_M, BLOCK_N]
        qk = tl.dot(qg, tl.trans(kg)).to(tl.float32)
        qk = tl.where(mask_n[None, :], qk, -1.0e9)

        row_max = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, row_max)

        alpha = tl.exp2((m_i - m_new) * LOG2E)
        p = tl.exp2((qk - m_new[:, None]) * LOG2E)
        p = tl.where(mask_n[None, :], p, 0.0)

        l_new = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = V_ptr + v_bh_off + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0, eviction_policy="evict_last").to(tl.float16)

        p16 = p.to(tl.float16)
        acc = acc * alpha[:, None] + tl.dot(p16, v).to(tl.float32)

        m_i = m_new
        l_i = l_new

    l_i = tl.where(mask_m, l_i, 1.0)
    out = acc / l_i[:, None]
    out = tl.where(mask_m[:, None] & mask_dv[None, :], out, 0.0)
    out = out.to(tl.float16)

    o_ptrs = O_ptr + o_bh_off + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=mask_m[:, None] & mask_dv[None, :])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Zk == Z and Hk == H and Zv == Z and Hv == H
    assert N == Nv
    assert Dq == Dk
    assert GQ.shape == Q.shape
    assert GK.shape == K.shape
    assert N == M  # problem setting says N matches M

    if Dq != 64 or Dv != 64:
        scale = 1.0 / math.sqrt(Dq)
        Qg = Q * torch.sigmoid(GQ)
        Kg = K * torch.sigmoid(GK)
        attn = torch.softmax(torch.matmul(Qg, Kg.transpose(-1, -2)) * scale, dim=-1)
        return torch.matmul(attn, V).to(torch.float16)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    # Heuristic tuning for L4 / these sizes
    if M <= 512:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 4
        num_stages = 4
    else:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 8
        num_stages = 4

    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        H=H,
        M_CTX=M,
        D_HEAD=Dq,
        D_V=Dv,
        N_CTX=N,
        SCALE=(1.0 / math.sqrt(Dq)),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=64,
        BLOCK_DV=64,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
'''


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"code": _KERNEL_CODE}