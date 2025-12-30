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
    Z: tl.constexpr, H: tl.constexpr,
    M: tl.int32, N: tl.int32,
    softmax_scale: tl.float32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr, D_VALUE: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    z = pid_bh // H
    h = pid_bh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    row_mask = offs_m < M

    q_ptrs = Q + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ + z * stride_gqz + h * stride_gqh + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float32)

    s_gq = 1.0 / (1.0 + tl.exp(-gq))
    q = q * s_gq

    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    k_base = K + z * stride_kz + h * stride_kh
    gk_base = GK + z * stride_gkz + h * stride_gkh
    v_base = V + z * stride_vz + h * stride_vh

    for start_n in range(0, N, BLOCK_N):
        n_mask = (start_n + offs_n) < N

        k_ptrs = k_base + (start_n + offs_n)[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = gk_base + (start_n + offs_n)[:, None] * stride_gkn + offs_d[None, :] * stride_gkd
        v_ptrs = v_base + (start_n + offs_n)[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        s_gk = 1.0 / (1.0 + tl.exp(-gk))
        k = k * s_gk

        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * softmax_scale
        qk = tl.where(n_mask[None, :], qk, -float('inf'))
        qk = tl.where(row_mask[:, None], qk, -float('inf'))

        m_ij = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.where(row_mask, tl.exp(m_i - m_i_new), 0.0)

        p = tl.exp(qk - m_i_new[:, None])
        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = tl.where(row_mask, m_i_new, m_i)

    l_safe = tl.where(row_mask, l_i, 1.0)
    out = acc / l_safe[:, None]

    out_ptrs = Out + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, out.to(out_ptrs.dtype.element_ty), mask=row_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 \
           and GQ.dtype == torch.float16 and GK.dtype == torch.float16, "All tensors must be float16"
    assert Q.shape[0] == K.shape[0] == V.shape[0] == GQ.shape[0] == GK.shape[0], "Batch (Z) mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1] == GQ.shape[1] == GK.shape[1], "Heads (H) mismatch"
    assert Q.shape[2] == GQ.shape[2], "Q and GQ M mismatch"
    assert K.shape[2] == V.shape[2] == GK.shape[2], "K/GK and V N mismatch"
    assert Q.shape[3] == K.shape[3] == GQ.shape[3] == GK.shape[3], "Dq mismatch"
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    Dv = V.shape[-1]
    assert Dq == Dk, "Q/K head dimension mismatch"

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    softmax_scale = 1.0 / math.sqrt(Dq)

    BLOCK_M = 64
    BLOCK_N = 64

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    qz, qh, qm, qd = Q.stride()
    kz, kh, kn, kd = K.stride()
    vz, vh, vn, vd = V.stride()
    gqz, gqh, gqm, gqd = GQ.stride()
    gkz, gkh, gkn, gkd = GK.stride()
    oz, oh, om, od = Out.stride()

    num_warps = 4
    num_stages = 3

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        qz, qh, qm, qd,
        kz, kh, kn, kd,
        vz, vh, vn, vd,
        gqz, gqh, gqm, gqd,
        gkz, gkh, gkn, gkd,
        oz, oh, om, od,
        Z, H,
        M, N,
        softmax_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D_HEAD=Dq, D_VALUE=Dv,
        num_warps=num_warps, num_stages=num_stages,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
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
    Z: tl.constexpr, H: tl.constexpr,
    M: tl.int32, N: tl.int32,
    softmax_scale: tl.float32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr, D_VALUE: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    z = pid_bh // H
    h = pid_bh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    row_mask = offs_m < M

    q_ptrs = Q + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ + z * stride_gqz + h * stride_gqh + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float32)

    s_gq = 1.0 / (1.0 + tl.exp(-gq))
    q = q * s_gq

    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    k_base = K + z * stride_kz + h * stride_kh
    gk_base = GK + z * stride_gkz + h * stride_gkh
    v_base = V + z * stride_vz + h * stride_vh

    for start_n in range(0, N, BLOCK_N):
        n_mask = (start_n + offs_n) < N

        k_ptrs = k_base + (start_n + offs_n)[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = gk_base + (start_n + offs_n)[:, None] * stride_gkn + offs_d[None, :] * stride_gkd
        v_ptrs = v_base + (start_n + offs_n)[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        s_gk = 1.0 / (1.0 + tl.exp(-gk))
        k = k * s_gk

        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * softmax_scale
        qk = tl.where(n_mask[None, :], qk, -float('inf'))
        qk = tl.where(row_mask[:, None], qk, -float('inf'))

        m_ij = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.where(row_mask, tl.exp(m_i - m_i_new), 0.0)

        p = tl.exp(qk - m_i_new[:, None])
        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = tl.where(row_mask, m_i_new, m_i)

    l_safe = tl.where(row_mask, l_i, 1.0)
    out = acc / l_safe[:, None]

    out_ptrs = Out + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, out.to(out_ptrs.dtype.element_ty), mask=row_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 \\
           and GQ.dtype == torch.float16 and GK.dtype == torch.float16, "All tensors must be float16"
    assert Q.shape[0] == K.shape[0] == V.shape[0] == GQ.shape[0] == GK.shape[0], "Batch (Z) mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1] == GQ.shape[1] == GK.shape[1], "Heads (H) mismatch"
    assert Q.shape[2] == GQ.shape[2], "Q and GQ M mismatch"
    assert K.shape[2] == V.shape[2] == GK.shape[2], "K/GK and V N mismatch"
    assert Q.shape[3] == K.shape[3] == GQ.shape[3] == GK.shape[3], "Dq mismatch"
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    Dv = V.shape[-1]
    assert Dq == Dk, "Q/K head dimension mismatch"

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    softmax_scale = 1.0 / math.sqrt(Dq)

    BLOCK_M = 64
    BLOCK_N = 64

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    qz, qh, qm, qd = Q.stride()
    kz, kh, kn, kd = K.stride()
    vz, vh, vn, vd = V.stride()
    gqz, gqh, gqm, gqd = GQ.stride()
    gkz, gkh, gkn, gkd = GK.stride()
    oz, oh, om, od = Out.stride()

    num_warps = 4
    num_stages = 3

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        qz, qh, qm, qd,
        kz, kh, kn, kd,
        vz, vh, vn, vd,
        gqz, gqh, gqm, gqd,
        gkz, gkh, gkn, gkd,
        oz, oh, om, od,
        Z, H,
        M, N,
        softmax_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D_HEAD=Dq, D_VALUE=Dv,
        num_warps=num_warps, num_stages=num_stages,
    )

    return Out
'''
        return {"code": code}