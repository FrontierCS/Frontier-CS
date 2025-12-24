import math
import os
import inspect
from typing import Dict, Tuple, Optional

import torch
import triton
import triton.language as tl


# ----------------------------
# Triton kernels
# ----------------------------

@triton.jit
def _attn_partials_kernel(
    Q_ptr, K_ptr, V_ptr,
    M_part_ptr, L_part_ptr, A_part_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_mq: tl.constexpr, stride_mc: tl.constexpr,
    stride_lq: tl.constexpr, stride_lc: tl.constexpr,
    stride_aq: tl.constexpr, stride_ac: tl.constexpr, stride_ad: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr, M: tl.constexpr,
    N,
    DQ: tl.constexpr, DV: tl.constexpr,
    BLOCK_N: tl.constexpr,
    scale,
):
    pid_q = tl.program_id(0)
    pid_c = tl.program_id(1)

    m_idx = pid_q % M
    t = pid_q // M
    h_idx = t % H
    z_idx = t // H

    q_offs = tl.arange(0, DQ)
    q_ptrs = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm + q_offs * stride_qd
    q = tl.load(q_ptrs, mask=q_offs < DQ, other=0.0).to(tl.float16)
    q_col = tl.reshape(q, (DQ, 1))

    n_start = pid_c * BLOCK_N
    n_offs = n_start + tl.arange(0, BLOCK_N)
    n_mask = n_offs < N

    k_ptrs = K_ptr + z_idx * stride_kz + h_idx * stride_kh + n_offs[:, None] * stride_kn + q_offs[None, :] * stride_kd
    k = tl.load(k_ptrs, mask=n_mask[:, None] & (q_offs[None, :] < DQ), other=0.0).to(tl.float16)

    scores = tl.dot(k, q_col, out_dtype=tl.float32)[:, 0]
    scores = scores * scale
    scores = tl.where(n_mask, scores, -float("inf"))

    m_part = tl.max(scores, axis=0)
    scores = scores - m_part
    p_f32 = tl.exp(scores).to(tl.float32)
    l_part = tl.sum(p_f32, axis=0)

    dv_offs = tl.arange(0, DV)
    v_ptrs = V_ptr + z_idx * stride_vz + h_idx * stride_vh + n_offs[:, None] * stride_vn + dv_offs[None, :] * stride_vd
    v = tl.load(v_ptrs, mask=n_mask[:, None] & (dv_offs[None, :] < DV), other=0.0).to(tl.float16)

    p_f16 = p_f32.to(tl.float16)
    p_row = tl.reshape(p_f16, (1, BLOCK_N))
    a_part = tl.dot(p_row, v, out_dtype=tl.float32)[0, :]

    m_out_ptr = M_part_ptr + pid_q * stride_mq + pid_c * stride_mc
    l_out_ptr = L_part_ptr + pid_q * stride_lq + pid_c * stride_lc
    tl.store(m_out_ptr, m_part)
    tl.store(l_out_ptr, l_part)

    a_out_ptrs = A_part_ptr + pid_q * stride_aq + pid_c * stride_ac + dv_offs * stride_ad
    tl.store(a_out_ptrs, a_part, mask=dv_offs < DV)


@triton.jit
def _attn_reduce_kernel(
    M_part_ptr, L_part_ptr, A_part_ptr,
    O_ptr,
    stride_mq: tl.constexpr, stride_mc: tl.constexpr,
    stride_lq: tl.constexpr, stride_lc: tl.constexpr,
    stride_aq: tl.constexpr, stride_ac: tl.constexpr, stride_ad: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr, M: tl.constexpr,
    DQ: tl.constexpr, DV: tl.constexpr,
    N_CHUNKS,
    MAX_CHUNKS: tl.constexpr,
):
    pid_q = tl.program_id(0)

    m_idx = pid_q % M
    t = pid_q // M
    h_idx = t % H
    z_idx = t // H

    m_global = -float("inf")
    for c in tl.static_range(0, MAX_CHUNKS):
        c_mask = c < N_CHUNKS
        m_c = tl.load(M_part_ptr + pid_q * stride_mq + c * stride_mc, mask=c_mask, other=-float("inf"))
        m_global = tl.maximum(m_global, m_c)

    l_total = 0.0
    acc = tl.zeros((DV,), dtype=tl.float32)
    dv_offs = tl.arange(0, DV)

    for c in tl.static_range(0, MAX_CHUNKS):
        c_mask = c < N_CHUNKS
        m_c = tl.load(M_part_ptr + pid_q * stride_mq + c * stride_mc, mask=c_mask, other=-float("inf"))
        l_c = tl.load(L_part_ptr + pid_q * stride_lq + c * stride_lc, mask=c_mask, other=0.0)
        alpha = tl.exp(m_c - m_global).to(tl.float32)
        w = l_c * alpha
        l_total += w
        a_ptrs = A_part_ptr + pid_q * stride_aq + c * stride_ac + dv_offs * stride_ad
        a_c = tl.load(a_ptrs, mask=c_mask & (dv_offs < DV), other=0.0).to(tl.float32)
        acc += a_c * alpha

    inv_l = 1.0 / l_total
    out = acc * inv_l
    out = out.to(tl.float16)

    o_ptrs = O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om + dv_offs * stride_od
    tl.store(o_ptrs, out, mask=dv_offs < DV)


@triton.jit
def _attn_singlepass_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr, M: tl.constexpr,
    N,
    DQ: tl.constexpr, DV: tl.constexpr,
    BLOCK_N: tl.constexpr,
    scale,
):
    pid_q = tl.program_id(0)

    m_idx = pid_q % M
    t = pid_q // M
    h_idx = t % H
    z_idx = t // H

    q_offs = tl.arange(0, DQ)
    q_ptrs = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm + q_offs * stride_qd
    q = tl.load(q_ptrs, mask=q_offs < DQ, other=0.0).to(tl.float16)
    q_col = tl.reshape(q, (DQ, 1))

    m_i = -float("inf")
    l_i = 0.0
    acc = tl.zeros((DV,), dtype=tl.float32)

    dv_offs = tl.arange(0, DV)

    n_blocks = tl.cdiv(N, BLOCK_N)
    for b in tl.static_range(0, 256):  # upper bound; masked by b < n_blocks
        b_mask = b < n_blocks
        n_start = b * BLOCK_N
        n_offs = n_start + tl.arange(0, BLOCK_N)
        n_mask = b_mask & (n_offs < N)

        k_ptrs = K_ptr + z_idx * stride_kz + h_idx * stride_kh + n_offs[:, None] * stride_kn + q_offs[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (q_offs[None, :] < DQ), other=0.0).to(tl.float16)

        scores = tl.dot(k, q_col, out_dtype=tl.float32)[:, 0] * scale
        scores = tl.where(n_mask, scores, -float("inf"))

        m_b = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, m_b)
        exp_old = tl.exp(m_i - m_new).to(tl.float32)
        p = tl.exp(scores - m_new).to(tl.float32)
        l_new = l_i * exp_old + tl.sum(p, axis=0)

        v_ptrs = V_ptr + z_idx * stride_vz + h_idx * stride_vh + n_offs[:, None] * stride_vn + dv_offs[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (dv_offs[None, :] < DV), other=0.0).to(tl.float16)

        p16 = p.to(tl.float16)
        p_row = tl.reshape(p16, (1, BLOCK_N))
        acc_b = tl.dot(p_row, v, out_dtype=tl.float32)[0, :]

        acc = acc * exp_old + acc_b
        m_i = m_new
        l_i = l_new

    out = (acc / l_i).to(tl.float16)
    o_ptrs = O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om + dv_offs * stride_od
    tl.store(o_ptrs, out, mask=dv_offs < DV)


# ----------------------------
# Python interface + caching
# ----------------------------

_SCRATCH_CACHE: Dict[Tuple[int, int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _get_scratch(device: torch.device, qhm: int, max_chunks: int, dv: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    key = (device.index if device.type == "cuda" else -1, qhm, max_chunks, dv)
    t = _SCRATCH_CACHE.get(key, None)
    if t is not None:
        m_part, l_part, a_part = t
        if (m_part.is_cuda and m_part.device == device and
            m_part.shape == (qhm, max_chunks) and
            l_part.shape == (qhm, max_chunks) and
            a_part.shape == (qhm, max_chunks, dv)):
            return t
    m_part = torch.empty((qhm, max_chunks), device=device, dtype=torch.float32)
    l_part = torch.empty((qhm, max_chunks), device=device, dtype=torch.float32)
    a_part = torch.empty((qhm, max_chunks, dv), device=device, dtype=torch.float32)
    _SCRATCH_CACHE[key] = (m_part, l_part, a_part)
    return m_part, l_part, a_part


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        raise ValueError("decoding_attn: Q, K, V must be CUDA tensors")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("decoding_attn: Q, K, V must be float16")
    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("decoding_attn: Q, K, V must be rank-4 tensors")

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    if Zk != Z or Zv != Z or Hk != H or Hv != H or Nv != N or DQk != DQ:
        raise ValueError("decoding_attn: shape mismatch among Q, K, V")

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    scale = 1.0 / math.sqrt(DQ)
    qhm = Z * H * M

    BLOCK_N = 256
    max_chunks = 32
    n_chunks = (N + BLOCK_N - 1) // BLOCK_N

    if n_chunks <= max_chunks:
        m_part, l_part, a_part = _get_scratch(Q.device, qhm, max_chunks, DV)

        grid1 = (qhm, n_chunks)
        _attn_partials_kernel[grid1](
            Q, K, V,
            m_part, l_part, a_part,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            m_part.stride(0), m_part.stride(1),
            l_part.stride(0), l_part.stride(1),
            a_part.stride(0), a_part.stride(1), a_part.stride(2),
            Z=Z, H=H, M=M,
            N=N,
            DQ=DQ, DV=DV,
            BLOCK_N=BLOCK_N,
            scale=scale,
            num_warps=8,
            num_stages=3,
        )

        grid2 = (qhm,)
        _attn_reduce_kernel[grid2](
            m_part, l_part, a_part,
            O,
            m_part.stride(0), m_part.stride(1),
            l_part.stride(0), l_part.stride(1),
            a_part.stride(0), a_part.stride(1), a_part.stride(2),
            O.stride(0), O.stride(1), O.stride(2), O.stride(3),
            Z=Z, H=H, M=M,
            DQ=DQ, DV=DV,
            N_CHUNKS=n_chunks,
            MAX_CHUNKS=max_chunks,
            num_warps=4,
            num_stages=2,
        )
        return O

    # Fallback for unusually large N (or very small BLOCK_N choices)
    grid = (qhm,)
    _attn_singlepass_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z=Z, H=H, M=M,
        N=N,
        DQ=DQ, DV=DV,
        BLOCK_N=128,
        scale=scale,
        num_warps=8,
        num_stages=3,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
