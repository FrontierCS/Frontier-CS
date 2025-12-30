import textwrap

KERNEL_CODE = textwrap.dedent(
    r"""
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
    H: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    LOG2E = 1.4426950408889634

    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    z = pid_bh // H
    h = pid_bh - z * H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, DQ)
    offs_dv = tl.arange(0, DV)

    q_mask_m = offs_m < M
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ_ptr + z * stride_gqz + h * stride_gqh + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=q_mask_m[:, None], other=0.0).to(tl.float16)
    gq = tl.load(gq_ptrs, mask=q_mask_m[:, None], other=0.0).to(tl.float16)

    gq_f = gq.to(tl.float32)
    gate_q = 1.0 / (1.0 + tl.exp2((-gq_f) * LOG2E))
    gate_q = gate_q.to(tl.float16)
    qg = (q * gate_q)
    qg = (qg * tl.full([], SCALE, tl.float16)).to(tl.float16)

    m_i = tl.full([BLOCK_M], -float("inf"), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DV], tl.float32)

    base_k = K_ptr + z * stride_kz + h * stride_kh
    base_gk = GK_ptr + z * stride_gkz + h * stride_gkh
    base_v = V_ptr + z * stride_vz + h * stride_vh

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = base_k + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
        gk_ptrs = base_gk + offs_n[None, :] * stride_gkn + offs_d[:, None] * stride_gkd

        k = tl.load(k_ptrs, mask=n_mask[None, :], other=0.0, cache_modifier="ca").to(tl.float16)
        gk = tl.load(gk_ptrs, mask=n_mask[None, :], other=0.0, cache_modifier="ca").to(tl.float16)

        gk_f = gk.to(tl.float32)
        gate_k = 1.0 / (1.0 + tl.exp2((-gk_f) * LOG2E))
        gate_k = gate_k.to(tl.float16)
        kg = (k * gate_k).to(tl.float16)

        qk = tl.dot(qg, kg).to(tl.float32)
        qk = tl.where(q_mask_m[:, None] & n_mask[None, :], qk, -float("inf"))

        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)

        alpha = tl.exp2((m_i - m_new) * LOG2E)
        p = tl.exp2((qk - m_new[:, None]) * LOG2E)

        l_new = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = base_v + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0, cache_modifier="ca").to(tl.float16)

        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v).to(tl.float32)

        m_i = m_new
        l_i = l_new

    out = acc / l_i[:, None]
    out = out.to(tl.float16)

    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=q_mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Zv == Z and Hk == H and Hv == H and Nv == N and DQk == DQ
    assert GQ.shape == Q.shape
    assert GK.shape == K.shape
    assert N == M
    assert DQ == 64 and DV == 64

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    BLOCK_M = 128
    BLOCK_N = 64
    num_warps = 4
    num_stages = 4

    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        stride_qz=stride_qz, stride_qh=stride_qh, stride_qm=stride_qm, stride_qd=stride_qd,
        stride_kz=stride_kz, stride_kh=stride_kh, stride_kn=stride_kn, stride_kd=stride_kd,
        stride_vz=stride_vz, stride_vh=stride_vh, stride_vn=stride_vn, stride_vd=stride_vd,
        stride_gqz=stride_gqz, stride_gqh=stride_gqh, stride_gqm=stride_gqm, stride_gqd=stride_gqd,
        stride_gkz=stride_gkz, stride_gkh=stride_gkh, stride_gkn=stride_gkn, stride_gkd=stride_gkd,
        stride_oz=stride_oz, stride_oh=stride_oh, stride_om=stride_om, stride_od=stride_od,
        H=H,
        M=M,
        N=N,
        DQ=DQ,
        DV=DV,
        SCALE=(1.0 / math.sqrt(DQ)),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}