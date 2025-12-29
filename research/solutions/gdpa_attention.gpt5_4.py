import torch
import triton
import triton.language as tl
import math


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def gdpa_fwd_kernel(Q, K, V, GQ, GK, Out,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
                    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    Z, H, M, N, Dq, Dv, scale,
                    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)
    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dq = offs_dq < Dq
    mask_dv = offs_dv < Dv

    # Load and gate Q
    q_ptrs = Q + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = GQ + z * stride_gqz + h * stride_gqh + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
    gate_q = 1.0 / (1.0 + tl.exp(-gq))
    qg = q * gate_q  # [BM, DQ]

    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Iterate over keys
    for start_n in range(0, N, BLOCK_N):
        offs_n_cur = start_n + offs_n
        mask_n = offs_n_cur < N

        # Load and gate K block: shape [DQ, BN]
        k_ptrs = K + z * stride_kz + h * stride_kh + offs_dq[:, None] * stride_kd + offs_n_cur[None, :] * stride_kn
        gk_ptrs = GK + z * stride_gkz + h * stride_gkh + offs_dq[:, None] * stride_gkd + offs_n_cur[None, :] * stride_gkn
        k = tl.load(k_ptrs, mask=mask_dq[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=mask_dq[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        gate_k = 1.0 / (1.0 + tl.exp(-gk))
        kg = k * gate_k  # [DQ, BN]

        # Compute scores [BM, BN]
        scores = tl.dot(qg, kg) * scale

        # Mask out-of-bounds rows and cols to -inf to ignore in softmax
        scores = tl.where(mask_m[:, None] & mask_n[None, :], scores, -float('inf'))

        # Streaming softmax update
        row_max = tl.max(scores, 1)
        m_new = tl.maximum(m_i, row_max)
        p = tl.exp(scores - m_new[:, None])

        row_sum = tl.sum(p, 1)
        l_new = l_i * tl.exp(m_i - m_new) + row_sum

        # Avoid div by zero; keep masked rows at zero contribution
        denom = tl.where(l_new > 0, l_new, 1.0)
        p_norm = p / denom[:, None]
        p_norm = tl.where(mask_m[:, None], p_norm, 0.0)

        alpha = tl.where(mask_m, (l_i * tl.exp(m_i - m_new)) / denom, 0.0)

        # Load V block [BN, DV]
        v_ptrs = V + z * stride_vz + h * stride_vh + offs_n_cur[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        acc = acc * alpha[:, None] + tl.dot(p_norm, v)

        m_i = m_new
        l_i = tl.where(mask_m, l_new, 0.0)

    # Store output
    out_ptrs = Out + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda):
        raise RuntimeError('All inputs must be CUDA tensors.')
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16, 'All inputs must be float16.'
    assert Q.shape[0] == K.shape[0] == V.shape[0] == GQ.shape[0] == GK.shape[0], 'Batch dim mismatch'
    assert Q.shape[1] == K.shape[1] == V.shape[1] == GQ.shape[1] == GK.shape[1], 'Head dim mismatch'
    assert Q.shape[2] == GQ.shape[2] and K.shape[2] == GK.shape[2], 'Gate shapes mismatch'
    Z, H, M, Dq = Q.shape
    _, _, N, Dqk = K.shape
    _, _, _, Dv = V.shape
    assert Dq == Dqk == GQ.shape[3] == GK.shape[3], 'Q/K feature dims mismatch'
    assert N == M, 'For GDPA attention, N must equal M'

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = Out.stride()

    scale = 1.0 / math.sqrt(Dq)

    # Tiling parameters
    def next_power_of_2(x: int) -> int:
        x = int(x)
        return 1 << ((x - 1).bit_length())

    BLOCK_DQ = min(128, next_power_of_2(Dq))
    BLOCK_DV = min(128, next_power_of_2(Dv))
    # Choose BM/BN and num_warps heuristically
    if Dv <= 64 and Dq <= 64:
        BLOCK_M = 64
        BLOCK_N = 64
        num_warps = 4
    else:
        BLOCK_M = 64
        BLOCK_N = 64
        num_warps = 8

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv, scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DQ=BLOCK_DQ, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps, num_stages=2
    )
    return Out
"""
        return {"code": code}