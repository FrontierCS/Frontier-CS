import math
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.jit
    def _gdpa_fwd_kernel(
        Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, D, Dv,
        scale,
        N_CTX: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_DQ: tl.constexpr,
        BLOCK_DV: tl.constexpr,
    ):
        pid_bh = tl.program_id(0)
        pid_m = tl.program_id(1)

        z = pid_bh // H
        h = pid_bh % H

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_dq = tl.arange(0, BLOCK_DQ)
        offs_dv = tl.arange(0, BLOCK_DV)

        mask_m = offs_m < M
        mask_dq = offs_dq < D
        mask_dv = offs_dv < Dv

        q_base = Q_ptr + z * stride_qz + h * stride_qh
        k_base = K_ptr + z * stride_kz + h * stride_kh
        v_base = V_ptr + z * stride_vz + h * stride_vh
        gq_base = GQ_ptr + z * stride_qz + h * stride_qh
        gk_base = GK_ptr + z * stride_kz + h * stride_kh
        o_base = Out_ptr + z * stride_oz + h * stride_oh

        # Load and gate Q: [BLOCK_M, BLOCK_DQ]
        q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
        gq_ptrs = gq_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd

        q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gq = tl.load(gq_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gq = 1.0 / (1.0 + tl.exp(-gq))
        qg = q * gq

        # Streaming softmax state
        m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
        l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
        acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

        offs_n = tl.arange(0, BLOCK_N)

        for start_n in range(0, N_CTX, BLOCK_N):
            n_indices = start_n + offs_n
            mask_n = n_indices < N_CTX

            # Load and gate K: [BLOCK_N, BLOCK_DQ]
            k_ptrs = k_base + n_indices[:, None] * stride_kn + offs_dq[None, :] * stride_kd
            gk_ptrs = gk_base + n_indices[:, None] * stride_kn + offs_dq[None, :] * stride_kd

            k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
            gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
            gk = 1.0 / (1.0 + tl.exp(-gk))
            kg = k * gk

            # Load V: [BLOCK_N, BLOCK_DV]
            v_ptrs = v_base + n_indices[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

            # Attention scores: [BLOCK_M, BLOCK_N]
            qk = tl.dot(qg, tl.trans(kg)) * scale
            qk = tl.where(mask_n[None, :], qk, -float("inf"))

            # Streaming softmax update
            m_i_new = tl.maximum(m_i, tl.max(qk, axis=1))
            qk_shift = qk - m_i_new[:, None]
            p = tl.exp(qk_shift)

            alpha = tl.exp(m_i - m_i_new)
            l_i = l_i * alpha + tl.sum(p, axis=1)
            acc = acc * alpha[:, None] + tl.dot(p, v)
            m_i = m_i_new

        out = acc / l_i[:, None]
        out_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(out_ptrs, out.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def _gdpa_attn_reference(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor,
                         GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Dq = Q.shape[-1]
    scale = 1.0 / math.sqrt(Dq)
    Qg = Q * torch.sigmoid(GQ)
    Kg = K * torch.sigmoid(GK)
    scores = torch.matmul(Qg, Kg.transpose(-2, -1)) * scale
    attn = torch.softmax(scores, dim=-1)
    out = torch.matmul(attn, V)
    return out


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor,
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
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

    if (triton is None or
            not Q.is_cuda or
            not K.is_cuda or
            not V.is_cuda or
            not GQ.is_cuda or
            not GK.is_cuda):
        return _gdpa_attn_reference(Q, K, V, GQ, GK)

    MAX_D = 128
    if Dq > MAX_D or Dv > MAX_D:
        return _gdpa_attn_reference(Q, K, V, GQ, GK)

    # Choose block sizes for Dq and Dv (next power of 2, capped)
    def _next_pow2(x: int) -> int:
        v = 1
        while v < x:
            v <<= 1
        return v

    BLOCK_DQ = min(MAX_D, _next_pow2(Dq))
    BLOCK_DV = min(MAX_D, _next_pow2(Dv))

    BLOCK_M = 64
    BLOCK_N = 64
    num_warps = 4
    num_stages = 2

    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    scale = 1.0 / math.sqrt(Dq)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = out.stride()

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, out,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, Dq, Dv,
        scale,
        N_CTX=N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DQ=BLOCK_DQ,
        BLOCK_DV=BLOCK_DV,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}