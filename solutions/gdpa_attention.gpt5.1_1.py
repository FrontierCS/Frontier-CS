import math
import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_HEAD_QK: tl.constexpr,
    D_HEAD_V: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)

    h = pid_bh % H
    z = pid_bh // H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n_init = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, D_HEAD_QK)
    offs_dv = tl.arange(0, D_HEAD_V)

    row_mask = offs_m < M

    # Load Q and GQ tiles
    q_ptrs = Q + (
        z * stride_qz
        + h * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_dq[None, :] * stride_qd
    )
    gq_ptrs = GQ + (
        z * stride_gqz
        + h * stride_gqh
        + offs_m[:, None] * stride_gqm
        + offs_dq[None, :] * stride_gqd
    )

    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=row_mask[:, None], other=0.0)

    # Apply gate on Q: Qg = Q * sigmoid(GQ)
    gq_fp32 = gq.to(tl.float32)
    gate_q_fp32 = 1.0 / (1.0 + tl.exp(-gq_fp32))
    gate_q = gate_q_fp32.to(q.dtype)
    q = q * gate_q

    # Initialize streaming softmax stats
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, D_HEAD_V], dtype=tl.float32)

    NEG_INF = -1e9

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_n_init
        n_mask = offs_n < N

        # Load K, GK, V tiles
        k_ptrs = K + (
            z * stride_kz
            + h * stride_kh
            + offs_n[:, None] * stride_kn
            + offs_dq[None, :] * stride_kd
        )
        gk_ptrs = GK + (
            z * stride_gkz
            + h * stride_gkh
            + offs_n[:, None] * stride_gkn
            + offs_dq[None, :] * stride_gkd
        )
        v_ptrs = V + (
            z * stride_vz
            + h * stride_vh
            + offs_n[:, None] * stride_vn
            + offs_dv[None, :] * stride_vd
        )

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0)
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)

        # Apply gate on K: Kg = K * sigmoid(GK)
        gk_fp32 = gk.to(tl.float32)
        gate_k_fp32 = 1.0 / (1.0 + tl.exp(-gk_fp32))
        gate_k = gate_k_fp32.to(k.dtype)
        k = k * gate_k

        # Compute attention logits: Qg @ Kg^T / sqrt(Dq)
        qk = tl.dot(q, tl.trans(k))
        qk = qk * scale
        qk = tl.where(n_mask[None, :], qk, NEG_INF)

        # Update streaming softmax stats
        max_qk = tl.max(qk, 1)
        m_i_new = tl.maximum(m_i, max_qk)
        m_i_hat = tl.where(row_mask, m_i_new, m_i)

        p = tl.exp(qk - m_i_hat[:, None])
        p = tl.where(row_mask[:, None], p, 0.0)

        alpha = tl.exp(m_i - m_i_hat)

        l_i = l_i * alpha + tl.sum(p, 1)

        p_dot = p.to(v.dtype)
        acc = acc * alpha[:, None] + tl.dot(p_dot, v)

        m_i = m_i_hat

    # Final normalization
    l_i = tl.where(row_mask, l_i, 1.0)
    inv_l_i = 1.0 / l_i
    out = acc * inv_l_i[:, None]

    # Store output
    o_ptrs = Out + (
        z * stride_oz
        + h * stride_oh
        + offs_m[:, None] * stride_om
        + offs_dv[None, :] * stride_od
    )
    tl.store(o_ptrs, out.to(tl.float16), mask=row_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.

    Args:
        Q:  (Z, H, M, Dq) float16 CUDA
        K:  (Z, H, N, Dq) float16 CUDA
        V:  (Z, H, N, Dv) float16 CUDA
        GQ: (Z, H, M, Dq) float16 CUDA
        GK: (Z, H, N, Dq) float16 CUDA

    Returns:
        (Z, H, M, Dv) float16 CUDA
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16

    Q = Q.contiguous()
    K = K.contiguous()
    V = V.contiguous()
    GQ = GQ.contiguous()
    GK = GK.contiguous()

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    Zgq, Hgq, Mgq, Dgq = GQ.shape
    Zgk, Hgk, Ngk, Dgk = GK.shape

    assert Z == Zk == Zv == Zgq == Zgk
    assert H == Hk == Hv == Hgq == Hgk
    assert M == Mgq
    assert N == Nv == Ngk
    assert Dq == Dqk == Dgq == Dgk

    device = Q.device
    Out = torch.empty((Z, H, M, Dv), device=device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = Out.stride()

    BLOCK_M = 64
    BLOCK_N = 64

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    scale = 1.0 / math.sqrt(Dq)

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        D_HEAD_QK=Dq,
        D_HEAD_V=Dv,
        num_warps=4,
        num_stages=2,
    )

    return Out
'''
        return {"code": code}
