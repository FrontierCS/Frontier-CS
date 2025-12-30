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
    Z, H, M, N,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
):
    pid_z_h = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_z_h // H
    h = pid_z_h % H

    if z >= Z:
        return

    Q_base = Q_ptr + z * stride_qz + h * stride_qh
    K_base = K_ptr + z * stride_kz + h * stride_kh
    V_base = V_ptr + z * stride_vz + h * stride_vh
    GQ_base = GQ_ptr + z * stride_gqz + h * stride_gqh
    GK_base = GK_ptr + z * stride_gkz + h * stride_gkh
    Out_base = Out_ptr + z * stride_oz + h * stride_oh

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    mask_m = offs_m < M

    q_ptrs = Q_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = GQ_base + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)

    q_f32 = q.to(tl.float32)
    gq_f32 = gq.to(tl.float32)
    gq_sig = 1.0 / (1.0 + tl.exp(-gq_f32))
    qg = q_f32 * gq_sig

    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = K_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        gk_ptrs = GK_base + offs_n[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)

        k_f32 = k.to(tl.float32)
        gk_f32 = gk.to(tl.float32)
        gk_sig = 1.0 / (1.0 + tl.exp(-gk_f32))
        kg = k_f32 * gk_sig

        scores = tl.dot(qg, tl.trans(kg)) * scale
        scores = tl.where(mask_n[None, :], scores, -float("inf"))

        curr_m = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, curr_m)

        exp_scores = tl.exp(scores - m_new[:, None])
        l_new = tl.exp(m_i - m_new) * l_i + tl.sum(exp_scores, axis=1)

        p = exp_scores / l_new[:, None]

        acc_scale = tl.exp(m_i - m_new) * (l_i / l_new)

        v_ptrs = V_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

        acc = acc * acc_scale[:, None] + tl.dot(p, v)

        m_i = m_new
        l_i = l_new

    out_ptrs = Out_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert GQ.dtype == torch.float16
    assert GK.dtype == torch.float16
    assert Q.shape[0] == K.shape[0] == V.shape[0] == GQ.shape[0] == GK.shape[0]
    assert Q.shape[1] == K.shape[1] == V.shape[1] == GQ.shape[1] == GK.shape[1]
    assert Q.shape[2] == GQ.shape[2]
    assert K.shape[2] == V.shape[2] == GK.shape[2]
    assert Q.shape[3] == K.shape[3] == GQ.shape[3] == GK.shape[3]

    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    Dv = V.shape[3]

    assert N == M

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64

    scale = 1.0 / math.sqrt(Dq)

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        D_HEAD=Dq,
        D_VALUE=Dv,
        num_warps=4,
        num_stages=2,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}