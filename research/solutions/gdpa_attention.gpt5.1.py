from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        code = '''import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q, K, V, GQ, GK, O,
    stride_qb, stride_qm, stride_qk,
    stride_kb, stride_kn, stride_kk,
    stride_vb, stride_vn, stride_vd,
    stride_gqb, stride_gqm, stride_gqk,
    stride_gkb, stride_gkn, stride_gkk,
    stride_ob, stride_om, stride_od,
    M, sm_scale,
    N_CTX: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_b = tl.program_id(0)
    pid_m = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)
    offs_v = tl.arange(0, D_VALUE)

    mask_m = offs_m < M

    # Load Q and GQ
    q_ptrs = Q + pid_b * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    gq_ptrs = GQ + pid_b * stride_gqb + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqk

    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)

    q = q.to(tl.float32)
    gq = gq.to(tl.float32)

    gate_q = tl.sigmoid(gq)
    qg = q * gate_q  # (BLOCK_M, D_HEAD) in float32

    NEG_INFINITY = -1e9

    m_i = tl.full((BLOCK_M,), NEG_INFINITY, dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        # Load K, GK, V blocks
        k_ptrs = K + pid_b * stride_kb + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
        gk_ptrs = GK + pid_b * stride_gkb + offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkk
        v_ptrs = V + pid_b * stride_vb + offs_n[:, None] * stride_vn + offs_v[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        k = k.to(tl.float32)
        gk = gk.to(tl.float32)
        v = v.to(tl.float32)

        gate_k = tl.sigmoid(gk)
        kg = k * gate_k  # (BLOCK_N, D_HEAD) in float32

        # Attention scores
        qk = tl.dot(qg, tl.trans(kg))  # (BLOCK_M, BLOCK_N)
        qk = qk * sm_scale

        # Apply masks: queries beyond M or keys beyond N_CTX
        qk = tl.where(mask_m[:, None] & mask_n[None, :], qk, NEG_INFINITY)

        # Numerically stable streaming softmax
        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = m_ij

    # Normalize
    o = acc / l_i[:, None]

    o_ptrs = O + pid_b * stride_ob + offs_m[:, None] * stride_om + offs_v[None, :] * stride_od
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.

    Args:
        Q: (Z, H, M, Dq) float16
        K: (Z, H, N, Dq) float16
        V: (Z, H, N, Dv) float16
        GQ: (Z, H, M, Dq) float16
        GK: (Z, H, N, Dq) float16

    Returns:
        (Z, H, M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert GQ.dtype == torch.float16
    assert GK.dtype == torch.float16

    Z, H, M, D_HEAD = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, D_VALUE = V.shape
    Zgq, Hgq, Mgq, Dgq = GQ.shape
    Zgk, Hgk, Ngk, Dgk = GK.shape

    assert Z == Zk == Zv == Zgq == Zgk
    assert H == Hk == Hv == Hgq == Hgk
    assert M == Mgq
    assert N == Nv == Ngk
    assert D_HEAD == Dk == Dgq == Dgk

    B = Z * H  # batch*heads

    Q_ = Q.view(B, M, D_HEAD)
    K_ = K.view(B, N, D_HEAD)
    V_ = V.view(B, N, D_VALUE)
    GQ_ = GQ.view(B, M, D_HEAD)
    GK_ = GK.view(B, N, D_HEAD)

    O_ = torch.empty((B, M, D_VALUE), dtype=torch.float16, device=Q.device)

    stride_qb, stride_qm, stride_qk = Q_.stride()
    stride_kb, stride_kn, stride_kk = K_.stride()
    stride_vb, stride_vn, stride_vd = V_.stride()
    stride_gqb, stride_gqm, stride_gqk = GQ_.stride()
    stride_gkb, stride_gkn, stride_gkk = GK_.stride()
    stride_ob, stride_om, stride_od = O_.stride()

    sm_scale = 1.0 / math.sqrt(D_HEAD)

    BLOCK_M = 64
    BLOCK_N = 64

    grid = (B, triton.cdiv(M, BLOCK_M))

    gdpa_fwd_kernel[grid](
        Q_, K_, V_, GQ_, GK_, O_,
        stride_qb, stride_qm, stride_qk,
        stride_kb, stride_kn, stride_kk,
        stride_vb, stride_vn, stride_vd,
        stride_gqb, stride_gqm, stride_gqk,
        stride_gkb, stride_gkn, stride_gkk,
        stride_ob, stride_om, stride_od,
        M, sm_scale,
        N_CTX=N,
        D_HEAD=D_HEAD,
        D_VALUE=D_VALUE,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=2,
    )

    return O_.view(Z, H, M, D_VALUE)
'''
        return {"code": code}
