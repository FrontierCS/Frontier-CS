import os
import textwrap


KERNEL_CODE = textwrap.dedent(
    r'''
import math
import torch
import triton
import triton.language as tl


@tl.inline
def _sigmoid_f32(x):
    return 1.0 / (1.0 + tl.exp(-x))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=4),
    ],
    key=['M'],
)
@triton.jit
def _gdpa_fwd(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qb: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kb: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vb: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_gqb: tl.constexpr, stride_gqm: tl.constexpr, stride_gqd: tl.constexpr,
    stride_gkb: tl.constexpr, stride_gkn: tl.constexpr, stride_gkd: tl.constexpr,
    stride_ob: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    M: tl.constexpr, N: tl.constexpr,
    D_HEAD: tl.constexpr, D_V: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)
    offs_v = tl.arange(0, D_V)

    q_ptrs = Q_ptr + pid_b * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ_ptr + pid_b * stride_gqb + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd
    q_mask = (offs_m[:, None] < M) & (offs_d[None, :] < D_HEAD)

    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    qg = (q * _sigmoid_f32(gq)).to(tl.float16)

    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, D_V), tl.float32)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = K_ptr + pid_b * stride_kb + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = GK_ptr + pid_b * stride_gkb + offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkd
        k_mask = n_mask[:, None] & (offs_d[None, :] < D_HEAD)

        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=k_mask, other=0.0).to(tl.float32)
        kg = (k * _sigmoid_f32(gk)).to(tl.float16)

        qk = tl.dot(qg, tl.trans(kg)) * SCALE
        qk = tl.where(n_mask[None, :], qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij

        v_ptrs = V_ptr + pid_b * stride_vb + offs_n[:, None] * stride_vn + offs_v[None, :] * stride_vd
        v_mask = n_mask[:, None] & (offs_v[None, :] < D_V)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float16)

        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        m_i = m_ij

    out = acc / l_i[:, None]
    o_ptrs = O_ptr + pid_b * stride_ob + offs_m[:, None] * stride_om + offs_v[None, :] * stride_od
    o_mask = (offs_m[:, None] < M) & (offs_v[None, :] < D_V)
    tl.store(o_ptrs, out.to(tl.float16), mask=o_mask)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and M == GQ.shape[2] and N == GK.shape[2] and N == Nv
    assert Dq == Dk == GQ.shape[3] == GK.shape[3]
    assert Dv == V.shape[3]
    assert Dq in (64,) and Dv in (64,)

    B = Z * H
    Q_ = Q.reshape(B, M, Dq)
    K_ = K.reshape(B, N, Dq)
    V_ = V.reshape(B, N, Dv)
    GQ_ = GQ.reshape(B, M, Dq)
    GK_ = GK.reshape(B, N, Dq)

    O_ = torch.empty((B, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qb, stride_qm, stride_qd = Q_.stride()
    stride_kb, stride_kn, stride_kd = K_.stride()
    stride_vb, stride_vn, stride_vd = V_.stride()
    stride_gqb, stride_gqm, stride_gqd = GQ_.stride()
    stride_gkb, stride_gkn, stride_gkd = GK_.stride()
    stride_ob, stride_om, stride_od = O_.stride()

    scale = 1.0 / math.sqrt(Dq)

    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), B)

    _gdpa_fwd[grid](
        Q_, K_, V_, GQ_, GK_, O_,
        stride_qb, stride_qm, stride_qd,
        stride_kb, stride_kn, stride_kd,
        stride_vb, stride_vn, stride_vd,
        stride_gqb, stride_gqm, stride_gqd,
        stride_gkb, stride_gkn, stride_gkd,
        stride_ob, stride_om, stride_od,
        M=M, N=N, D_HEAD=Dq, D_V=Dv, SCALE=scale,
    )

    return O_.reshape(Z, H, M, Dv)
'''
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
