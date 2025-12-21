import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def gdpa_fwd_kernel(
    Q, K, V, GQ, GK, O,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale: tl.float32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_bh = tl.program_id(axis=1)
    z = pid_bh // H
    h = pid_bh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_bn = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    m_mask = offs_m < M

    # bases
    q_base = Q + z * stride_qz + h * stride_qh
    gq_base = GQ + z * stride_gqz + h * stride_gqh
    k_base = K + z * stride_kz + h * stride_kh
    gk_base = GK + z * stride_gkz + h * stride_gkh
    v_base = V + z * stride_vz + h * stride_vh
    o_base = O + z * stride_oz + h * stride_oh

    # Loop over DV tiles
    dv_start = 0
    while dv_start < Dv:
        cur_dv = tl.minimum(Dv - dv_start, BLOCK_DV)
        dv_mask = (dv_start + offs_dv) < Dv

        # accumulators
        m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
        l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
        acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

        # Loop along N dimension
        n_start = 0
        while n_start < N:
            cur_bn = tl.minimum(N - n_start, BLOCK_N)
            n_mask = (n_start + offs_bn) < N

            # Compute logits = qg @ kg^T over Dq in chunks
            logits = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

            d_start = 0
            while d_start < Dq:
                cur_dq = tl.minimum(Dq - d_start, BLOCK_DQ)
                dq_mask = (d_start + offs_dq) < Dq

                # load Q and GQ slices
                q_ptrs = q_base + offs_m[:, None] * stride_qm + (d_start + offs_dq)[None, :] * stride_qd
                gq_ptrs = gq_base + offs_m[:, None] * stride_gqm + (d_start + offs_dq)[None, :] * stride_gqd

                q = tl.load(q_ptrs, mask=m_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                gqv = tl.load(gq_ptrs, mask=m_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                # sigmoid(gq)
                gq_sig = 1.0 / (1.0 + tl.exp(-gqv))
                qg = q * gq_sig  # [BM, d]

                # load K and GK slices
                k_ptrs = k_base + (n_start + offs_bn)[:, None] * stride_kn + (d_start + offs_dq)[None, :] * stride_kd
                gk_ptrs = gk_base + (n_start + offs_bn)[:, None] * stride_gkn + (d_start + offs_dq)[None, :] * stride_gkd

                k = tl.load(k_ptrs, mask=n_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                gkv = tl.load(gk_ptrs, mask=n_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                gk_sig = 1.0 / (1.0 + tl.exp(-gkv))
                kg = k * gk_sig  # [BN, d]

                # dot accumulate
                logits += tl.dot(qg, tl.trans(kg))

                d_start += BLOCK_DQ

            # scale
            logits = logits * sm_scale

            # mask out invalid BN columns by setting -inf
            logits = tl.where(n_mask[None, :], logits, -float('inf'))

            # streaming softmax update
            m_tile = tl.max(logits, 1)
            new_m = tl.maximum(m_i, m_tile)
            p = tl.exp(logits - new_m[:, None])  # unnormalized probabilities at scale new_m

            alpha = tl.exp(m_i - new_m)
            l_i = l_i * alpha + tl.sum(p, 1)

            # load V tile for current dv block and accumulate
            v_ptrs = v_base + (n_start + offs_bn)[:, None] * stride_vn + (dv_start + offs_dv)[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)

            acc = acc * alpha[:, None] + tl.dot(p, v)

            m_i = new_m
            n_start += BLOCK_N

        # Normalize
        out = acc / l_i[:, None]

        # store result
        o_ptrs = o_base + offs_m[:, None] * stride_om + (dv_start + offs_dv)[None, :] * stride_od
        tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])

        dv_start += BLOCK_DV


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4 and GQ.dim() == 4 and GK.dim() == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    Zgq, Hgq, Mgq, Dqgq = GQ.shape
    Zgk, Hgk, Ngk, Dqgk = GK.shape
    assert Z == Zk == Zv == Zgq == Zgk
    assert H == Hk == Hv == Hgq == Hgk
    assert M == Mgq and N == Nv == Ngk
    assert Dq == Dqk == Dqgq == Dqgk

    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()
    GQc = GQ.contiguous()
    GKc = GK.contiguous()

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    sm_scale = 1.0 / math.sqrt(Dq)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)

    gdpa_fwd_kernel[grid](
        Qc, Kc, Vc, GQc, GKc, O,
        Z, H, M, N, Dq, Dv,
        Qc.stride(0), Qc.stride(1), Qc.stride(2), Qc.stride(3),
        Kc.stride(0), Kc.stride(1), Kc.stride(2), Kc.stride(3),
        Vc.stride(0), Vc.stride(1), Vc.stride(2), Vc.stride(3),
        GQc.stride(0), GQc.stride(1), GQc.stride(2), GQc.stride(3),
        GKc.stride(0), GKc.stride(1), GKc.stride(2), GKc.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def gdpa_fwd_kernel(
    Q, K, V, GQ, GK, O,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale: tl.float32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_bh = tl.program_id(axis=1)
    z = pid_bh // H
    h = pid_bh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_bn = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    m_mask = offs_m < M

    # bases
    q_base = Q + z * stride_qz + h * stride_qh
    gq_base = GQ + z * stride_gqz + h * stride_gqh
    k_base = K + z * stride_kz + h * stride_kh
    gk_base = GK + z * stride_gkz + h * stride_gkh
    v_base = V + z * stride_vz + h * stride_vh
    o_base = O + z * stride_oz + h * stride_oh

    # Loop over DV tiles
    dv_start = 0
    while dv_start < Dv:
        cur_dv = tl.minimum(Dv - dv_start, BLOCK_DV)
        dv_mask = (dv_start + offs_dv) < Dv

        # accumulators
        m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
        l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
        acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

        # Loop along N dimension
        n_start = 0
        while n_start < N:
            cur_bn = tl.minimum(N - n_start, BLOCK_N)
            n_mask = (n_start + offs_bn) < N

            # Compute logits = qg @ kg^T over Dq in chunks
            logits = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

            d_start = 0
            while d_start < Dq:
                cur_dq = tl.minimum(Dq - d_start, BLOCK_DQ)
                dq_mask = (d_start + offs_dq) < Dq

                # load Q and GQ slices
                q_ptrs = q_base + offs_m[:, None] * stride_qm + (d_start + offs_dq)[None, :] * stride_qd
                gq_ptrs = gq_base + offs_m[:, None] * stride_gqm + (d_start + offs_dq)[None, :] * stride_gqd

                q = tl.load(q_ptrs, mask=m_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                gqv = tl.load(gq_ptrs, mask=m_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                # sigmoid(gq)
                gq_sig = 1.0 / (1.0 + tl.exp(-gqv))
                qg = q * gq_sig  # [BM, d]

                # load K and GK slices
                k_ptrs = k_base + (n_start + offs_bn)[:, None] * stride_kn + (d_start + offs_dq)[None, :] * stride_kd
                gk_ptrs = gk_base + (n_start + offs_bn)[:, None] * stride_gkn + (d_start + offs_dq)[None, :] * stride_gkd

                k = tl.load(k_ptrs, mask=n_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                gkv = tl.load(gk_ptrs, mask=n_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
                gk_sig = 1.0 / (1.0 + tl.exp(-gkv))
                kg = k * gk_sig  # [BN, d]

                # dot accumulate
                logits += tl.dot(qg, tl.trans(kg))

                d_start += BLOCK_DQ

            # scale
            logits = logits * sm_scale

            # mask out invalid BN columns by setting -inf
            logits = tl.where(n_mask[None, :], logits, -float('inf'))

            # streaming softmax update
            m_tile = tl.max(logits, 1)
            new_m = tl.maximum(m_i, m_tile)
            p = tl.exp(logits - new_m[:, None])  # unnormalized probabilities at scale new_m

            alpha = tl.exp(m_i - new_m)
            l_i = l_i * alpha + tl.sum(p, 1)

            # load V tile for current dv block and accumulate
            v_ptrs = v_base + (n_start + offs_bn)[:, None] * stride_vn + (dv_start + offs_dv)[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)

            acc = acc * alpha[:, None] + tl.dot(p, v)

            m_i = new_m
            n_start += BLOCK_N

        # Normalize
        out = acc / l_i[:, None]

        # store result
        o_ptrs = o_base + offs_m[:, None] * stride_om + (dv_start + offs_dv)[None, :] * stride_od
        tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])

        dv_start += BLOCK_DV


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4 and GQ.dim() == 4 and GK.dim() == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    Zgq, Hgq, Mgq, Dqgq = GQ.shape
    Zgk, Hgk, Ngk, Dqgk = GK.shape
    assert Z == Zk == Zv == Zgq == Zgk
    assert H == Hk == Hv == Hgq == Hgk
    assert M == Mgq and N == Nv == Ngk
    assert Dq == Dqk == Dqgq == Dqgk

    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()
    GQc = GQ.contiguous()
    GKc = GK.contiguous()

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    sm_scale = 1.0 / math.sqrt(Dq)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)

    gdpa_fwd_kernel[grid](
        Qc, Kc, Vc, GQc, GKc, O,
        Z, H, M, N, Dq, Dv,
        Qc.stride(0), Qc.stride(1), Qc.stride(2), Qc.stride(3),
        Kc.stride(0), Kc.stride(1), Kc.stride(2), Kc.stride(3),
        Vc.stride(0), Vc.stride(1), Vc.stride(2), Vc.stride(3),
        GQc.stride(0), GQc.stride(1), GQc.stride(2), GQc.stride(3),
        GKc.stride(0), GKc.stride(1), GKc.stride(2), GKc.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
    )
    return O
'''
        return {"code": code}
