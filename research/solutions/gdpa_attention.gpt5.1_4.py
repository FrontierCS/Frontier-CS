import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_z_h = tl.program_id(axis=0)
    pid_m = tl.program_id(axis=1)

    z = pid_z_h // H
    h = pid_z_h % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DMODEL)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dq = offs_dq < Dq
    mask_dv = offs_dv < Dv

    # Load gated Q: Qg = Q * sigmoid(GQ)
    q_ptrs = Q_ptr + (
        z * stride_qz
        + h * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_dq[None, :] * stride_qd
    )
    gq_ptrs = GQ_ptr + (
        z * stride_gqz
        + h * stride_gqh
        + offs_m[:, None] * stride_gqm
        + offs_dq[None, :] * stride_gqd
    )

    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0)

    q = q.to(tl.float32)
    gq = gq.to(tl.float32)
    gate_q = tl.sigmoid(gq)
    q = q * gate_q  # Qg

    # Initialize streaming softmax state
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    # Loop over K/V blocks along N dimension
    n_start = 0
    while n_start < N:
        n_idx = n_start + offs_n
        mask_n = n_idx < N

        # Load gated K: Kg = K * sigmoid(GK)
        k_ptrs = K_ptr + (
            z * stride_kz
            + h * stride_kh
            + n_idx[:, None] * stride_kn
            + offs_dq[None, :] * stride_kd
        )
        gk_ptrs = GK_ptr + (
            z * stride_gkz
            + h * stride_gkh
            + n_idx[:, None] * stride_gkn
            + offs_dq[None, :] * stride_gkd
        )

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0)

        k = k.to(tl.float32)
        gk = gk.to(tl.float32)
        gate_k = tl.sigmoid(gk)
        k = k * gate_k  # Kg

        # Compute attention scores for this block: [BLOCK_M, BLOCK_N]
        qk = tl.dot(q, tl.trans(k))  # [BM, BN]
        qk = qk * scale

        # Numerically stable streaming softmax
        m_i_new = tl.maximum(m_i, tl.max(qk, axis=1))
        qk_shifted = qk - m_i_new[:, None]
        p = tl.exp(qk_shifted)
        l_i_new = l_i * tl.exp(m_i - m_i_new) + tl.sum(p, axis=1)

        # Update accumulator
        alpha = (l_i * tl.exp(m_i - m_i_new)) / l_i_new
        beta = 1.0 / l_i_new

        # Load V block: [BLOCK_N, BLOCK_DV]
        v_ptrs = V_ptr + (
            z * stride_vz
            + h * stride_vh
            + n_idx[:, None] * stride_vn
            + offs_dv[None, :] * stride_vd
        )
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)
        v = v.to(tl.float32)

        # Attention * V for this block
        att_block = tl.dot(p, v)  # [BM, DV]

        acc = acc * alpha[:, None] + att_block * beta[:, None]

        m_i = m_i_new
        l_i = l_i_new

        n_start += BLOCK_N

    # Write output
    out_ptrs = Out_ptr + (
        z * stride_oz
        + h * stride_oh
        + offs_m[:, None] * stride_om
        + offs_dv[None, :] * stride_od
    )
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def _gdpa_attn_ref(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor,
                   GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    scale = 1.0 / math.sqrt(Dq)

    Qg = Q * torch.sigmoid(GQ)
    Kg = K * torch.sigmoid(GK)

    scores = torch.matmul(Qg.to(torch.float32),
                          Kg.to(torch.float32).transpose(-2, -1)) * scale
    attn = torch.softmax(scores, dim=-1)
    out = torch.matmul(attn, V.to(torch.float32))
    return out.to(Q.dtype)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor,
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16

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

    # Fallback to reference implementation for unsupported dimensions
    MAX_DMODEL = 64
    MAX_DV = 64
    if Dq > MAX_DMODEL or Dv > MAX_DV:
        return _gdpa_attn_ref(Q, K, V, GQ, GK)

    scale = 1.0 / math.sqrt(float(Dq))

    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    # Extract strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = out.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    grid = (Z * H, (M + BLOCK_M - 1) // BLOCK_M)

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, out,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
