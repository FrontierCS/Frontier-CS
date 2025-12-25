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
    Z, H, M,
    scale,
    N_CTX: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_zh = tl.program_id(axis=0)
    pid_m = tl.program_id(axis=1)

    h = pid_zh % H
    z = pid_zh // H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_dq = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    # Load Q and GQ, apply gating: Qg = Q * sigmoid(GQ)
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

    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)  # float16
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)  # float16

    gq_f32 = gq.to(tl.float32)
    sig_gq_f32 = 1.0 / (1.0 + tl.exp(-gq_f32))
    sig_gq = sig_gq_f32.to(tl.float16)
    qg = q * sig_gq  # gated Q, float16

    neg_inf = -1.0e9
    m_i = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    for start_n in tl.static_range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        # Load K and GK, apply gating: Kg = K * sigmoid(GK)
        k_ptrs = K_ptr + (
            z * stride_kz
            + h * stride_kh
            + offs_n[:, None] * stride_kn
            + offs_dq[None, :] * stride_kd
        )
        gk_ptrs = GK_ptr + (
            z * stride_gkz
            + h * stride_gkh
            + offs_n[:, None] * stride_gkn
            + offs_dq[None, :] * stride_gkd
        )

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)  # float16
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)  # float16

        gk_f32 = gk.to(tl.float32)
        sig_gk_f32 = 1.0 / (1.0 + tl.exp(-gk_f32))
        sig_gk = sig_gk_f32.to(tl.float16)
        kg = k * sig_gk  # gated K, float16

        # Attention scores: [BLOCK_M, BLOCK_N], float32
        qk = tl.dot(qg, tl.trans(kg), out_dtype=tl.float32)
        qk = qk * scale
        qk = tl.where(mask_n[None, :], qk, neg_inf)

        m_i_new = tl.maximum(m_i, tl.max(qk, axis=1))
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(qk - m_i_new[:, None])

        # Load V
        v_ptrs = V_ptr + (
            z * stride_vz
            + h * stride_vh
            + offs_n[:, None] * stride_vn
            + offs_dv[None, :] * stride_vd
        )
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        v_f32 = v.to(tl.float32)

        l_i = l_i * alpha + tl.sum(p, axis=1)
        pv = tl.dot(p, v_f32)  # [BLOCK_M, D_VALUE], float32
        acc = acc * alpha[:, None] + pv

        m_i = m_i_new

    out = acc / l_i[:, None]
    out = out.to(tl.float16)

    out_ptrs = Out_ptr + (
        z * stride_oz
        + h * stride_oh
        + offs_m[:, None] * stride_om
        + offs_dv[None, :] * stride_od
    )
    mask_out = mask_m[:, None]
    tl.store(out_ptrs, out, mask=mask_out)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    _, _, _, Dv = V.shape

    assert Dq == Dk, "Q and K must have the same head dimension"
    assert N == M, "GDPA assumes N == M (sequence lengths match)"
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert GQ.dtype == torch.float16
    assert GK.dtype == torch.float16

    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()
    GQc = GQ.contiguous()
    GKc = GK.contiguous()

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    BLOCK_M = 64
    BLOCK_N = 64

    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    scale = 1.0 / math.sqrt(Dq)

    gdpa_fwd_kernel[grid](
        Qc, Kc, Vc, GQc, GKc, Out,
        Qc.stride(0), Qc.stride(1), Qc.stride(2), Qc.stride(3),
        Kc.stride(0), Kc.stride(1), Kc.stride(2), Kc.stride(3),
        Vc.stride(0), Vc.stride(1), Vc.stride(2), Vc.stride(3),
        GQc.stride(0), GQc.stride(1), GQc.stride(2), GQc.stride(3),
        GKc.stride(0), GKc.stride(1), GKc.stride(2), GKc.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        scale,
        N_CTX=N,
        D_HEAD=Dq,
        D_VALUE=Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=2,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": __file__}
        except NameError:
            import sys
            import inspect
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
