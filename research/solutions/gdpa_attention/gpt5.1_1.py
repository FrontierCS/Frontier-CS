import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_d = offs_d < Dq
    mask_dv = offs_dv < Dv

    z = pid_bh // H
    h = pid_bh % H

    q_offset = z * stride_qz + h * stride_qh
    gq_offset = z * stride_gqz + h * stride_gqh

    q_ptrs = Q_ptr + q_offset + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ_ptr + gq_offset + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)

    q_f32 = q.to(tl.float32)
    gq_f32 = gq.to(tl.float32)
    gate_q = tl.sigmoid(gq_f32)
    qg = (q_f32 * gate_q).to(tl.float16)

    neg_inf = -float("inf")

    m_i = tl.where(mask_m, neg_inf, 0.0)
    l_i = tl.where(mask_m, 0.0, 1.0)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    k_base = z * stride_kz + h * stride_kh
    gk_base = z * stride_gkz + h * stride_gkh
    v_base = z * stride_vz + h * stride_vh
    o_base = z * stride_oz + h * stride_oh

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = K_ptr + k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = GK_ptr + gk_base + offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkd
        v_ptrs = V_ptr + v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)

        k_f32 = k.to(tl.float32)
        gk_f32 = gk.to(tl.float32)
        gate_k = tl.sigmoid(gk_f32)
        kg = (k_f32 * gate_k).to(tl.float16)

        v_f32 = v.to(tl.float32)

        logits = tl.dot(qg, tl.trans(kg))
        logits = logits * sm_scale

        logits = tl.where(mask_m[:, None] & mask_n[None, :], logits, neg_inf)

        current_max = tl.max(logits, axis=1)
        m_i_new = tl.maximum(m_i, current_max)

        exp_m = tl.exp(m_i - m_i_new)
        p = tl.exp(logits - m_i_new[:, None])
        l_curr = tl.sum(p, axis=1)
        l_i_new = exp_m * l_i + l_curr

        pv = tl.dot(p, v_f32)

        scale_old = tl.where(l_i_new > 0, exp_m * l_i / l_i_new, 0.0)
        scale_new = tl.where(l_i_new > 0, 1.0 / l_i_new, 0.0)

        acc = acc * scale_old[:, None] + pv * scale_new[:, None]

        m_i = m_i_new
        l_i = l_i_new

    o_ptrs = O_ptr + o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def _next_power_of_2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << ((x - 1).bit_length())


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv
    assert H == Hk == Hv
    assert Dq == Dqk
    assert N == Nv

    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert GQ.dtype == torch.float16
    assert GK.dtype == torch.float16

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = _next_power_of_2(Dq)
    BLOCK_DV = _next_power_of_2(Dv)

    sm_scale = 1.0 / math.sqrt(Dq)

    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    num_warps = 4

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=num_warps,
        num_stages=2,
    )

    return O
'''
        return {"code": code}