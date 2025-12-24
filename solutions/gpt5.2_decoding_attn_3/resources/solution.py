import math
import os
from typing import Dict, Tuple, Optional

import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.jit
    def _decoding_attn_stage1(
        Q_ptr,
        K_ptr,
        V_ptr,
        M_ptr,
        L_ptr,
        A_ptr,
        sm_scale,
        N,
        stride_qz: tl.constexpr,
        stride_qh: tl.constexpr,
        stride_qm: tl.constexpr,
        stride_qd: tl.constexpr,
        stride_kz: tl.constexpr,
        stride_kh: tl.constexpr,
        stride_kn: tl.constexpr,
        stride_kd: tl.constexpr,
        stride_vz: tl.constexpr,
        stride_vh: tl.constexpr,
        stride_vn: tl.constexpr,
        stride_vd: tl.constexpr,
        stride_mz: tl.constexpr,
        stride_mh: tl.constexpr,
        stride_mm: tl.constexpr,
        stride_mb: tl.constexpr,
        stride_lz: tl.constexpr,
        stride_lh: tl.constexpr,
        stride_lm: tl.constexpr,
        stride_lb: tl.constexpr,
        stride_az: tl.constexpr,
        stride_ah: tl.constexpr,
        stride_am: tl.constexpr,
        stride_ab: tl.constexpr,
        stride_ad: tl.constexpr,
        H: tl.constexpr,
        Mq: tl.constexpr,
        DQ: tl.constexpr,
        DV: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_q = tl.program_id(0)
        pid_b = tl.program_id(1)

        m_idx = pid_q % Mq
        h_idx = (pid_q // Mq) % H
        z_idx = pid_q // (H * Mq)

        q_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
        k_ptr = K_ptr + z_idx * stride_kz + h_idx * stride_kh
        v_ptr = V_ptr + z_idx * stride_vz + h_idx * stride_vh

        d_off = tl.arange(0, DQ)
        q = tl.load(q_ptr + d_off * stride_qd).to(tl.float16)

        n0 = pid_b * BLOCK_N
        n_off = n0 + tl.arange(0, BLOCK_N)
        n_mask = n_off < N

        k = tl.load(
            k_ptr + n_off[:, None] * stride_kn + d_off[None, :] * stride_kd,
            mask=n_mask[:, None],
            other=0.0,
        ).to(tl.float16)

        scores = tl.dot(k, q[:, None])[:, 0].to(tl.float32) * sm_scale
        m_block = tl.max(scores, axis=0)
        p16 = tl.exp(scores - m_block).to(tl.float16)
        l_block = tl.sum(p16.to(tl.float32), axis=0)

        dv_off = tl.arange(0, DV)
        v = tl.load(
            v_ptr + n_off[:, None] * stride_vn + dv_off[None, :] * stride_vd,
            mask=n_mask[:, None],
            other=0.0,
        ).to(tl.float16)

        acc = tl.dot(p16[None, :], v)[0, :].to(tl.float32)

        tl.store(
            M_ptr + z_idx * stride_mz + h_idx * stride_mh + m_idx * stride_mm + pid_b * stride_mb,
            m_block,
        )
        tl.store(
            L_ptr + z_idx * stride_lz + h_idx * stride_lh + m_idx * stride_lm + pid_b * stride_lb,
            l_block,
        )
        tl.store(
            A_ptr
            + z_idx * stride_az
            + h_idx * stride_ah
            + m_idx * stride_am
            + pid_b * stride_ab
            + dv_off * stride_ad,
            acc,
        )

    @triton.jit
    def _decoding_attn_stage2(
        M_ptr,
        L_ptr,
        A_ptr,
        O_ptr,
        stride_mz: tl.constexpr,
        stride_mh: tl.constexpr,
        stride_mm: tl.constexpr,
        stride_mb: tl.constexpr,
        stride_lz: tl.constexpr,
        stride_lh: tl.constexpr,
        stride_lm: tl.constexpr,
        stride_lb: tl.constexpr,
        stride_az: tl.constexpr,
        stride_ah: tl.constexpr,
        stride_am: tl.constexpr,
        stride_ab: tl.constexpr,
        stride_ad: tl.constexpr,
        stride_oz: tl.constexpr,
        stride_oh: tl.constexpr,
        stride_om: tl.constexpr,
        stride_od: tl.constexpr,
        H: tl.constexpr,
        Mq: tl.constexpr,
        DV: tl.constexpr,
        B: tl.constexpr,
    ):
        pid_q = tl.program_id(0)

        m_idx = pid_q % Mq
        h_idx = (pid_q // Mq) % H
        z_idx = pid_q // (H * Mq)

        m_ptr = M_ptr + z_idx * stride_mz + h_idx * stride_mh + m_idx * stride_mm
        l_ptr = L_ptr + z_idx * stride_lz + h_idx * stride_lh + m_idx * stride_lm
        a_ptr = A_ptr + z_idx * stride_az + h_idx * stride_ah + m_idx * stride_am

        m_g = -float("inf")
        for b in tl.static_range(0, B):
            m_b = tl.load(m_ptr + b * stride_mb).to(tl.float32)
            m_g = tl.maximum(m_g, m_b)

        l_g = 0.0
        dv_off = tl.arange(0, DV)
        acc_g = tl.zeros([DV], dtype=tl.float32)

        for b in tl.static_range(0, B):
            m_b = tl.load(m_ptr + b * stride_mb).to(tl.float32)
            l_b = tl.load(l_ptr + b * stride_lb).to(tl.float32)
            w = tl.exp(m_b - m_g)
            l_g += l_b * w
            a_b = tl.load(a_ptr + b * stride_ab + dv_off * stride_ad).to(tl.float32)
            acc_g += a_b * w

        out = acc_g / l_g
        tl.store(
            O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om + dv_off * stride_od,
            out.to(tl.float16),
        )


_tmp_cache: Dict[Tuple[int, int, int, int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _get_tmp(device: torch.device, Z: int, H: int, M: int, B: int, DV: int):
    key = (device.index if device.type == "cuda" else -1, Z, H, M, B, DV)
    buf = _tmp_cache.get(key, None)
    if buf is not None:
        m, l, a = buf
        if m.is_cuda and m.device == device and l.device == device and a.device == device:
            return m, l, a
    m = torch.empty((Z, H, M, B), device=device, dtype=torch.float32)
    l = torch.empty((Z, H, M, B), device=device, dtype=torch.float32)
    a = torch.empty((Z, H, M, B, DV), device=device, dtype=torch.float32)
    _tmp_cache[key] = (m, l, a)
    return m, l, a


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if triton is None or (not Q.is_cuda) or (not K.is_cuda) or (not V.is_cuda):
        DQ = Q.shape[-1]
        sm_scale = 1.0 / math.sqrt(DQ)
        att = torch.matmul(Q.to(torch.float32), K.transpose(-1, -2).to(torch.float32)) * sm_scale
        p = torch.softmax(att, dim=-1)
        out = torch.matmul(p, V.to(torch.float32)).to(Q.dtype)
        return out

    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, Mq, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Hk == H and DQk == DQ
    assert Zv == Z and Hv == H and Nv == N
    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype == Q.dtype and V.dtype == Q.dtype
    assert DQ % 16 == 0 and DV % 16 == 0

    if N <= 2048:
        BLOCK_N = 64
        num_warps = 4
        num_stages = 3
    else:
        BLOCK_N = 128
        num_warps = 4
        num_stages = 4

    B = (N + BLOCK_N - 1) // BLOCK_N
    tmp_m, tmp_l, tmp_a = _get_tmp(Q.device, Z, H, Mq, B, DV)
    out = torch.empty((Z, H, Mq, DV), device=Q.device, dtype=torch.float16)

    sm_scale = 1.0 / math.sqrt(DQ)

    grid1 = (Z * H * Mq, B)
    _decoding_attn_stage1[grid1](
        Q,
        K,
        V,
        tmp_m,
        tmp_l,
        tmp_a,
        sm_scale,
        N,
        stride_qz=Q.stride(0),
        stride_qh=Q.stride(1),
        stride_qm=Q.stride(2),
        stride_qd=Q.stride(3),
        stride_kz=K.stride(0),
        stride_kh=K.stride(1),
        stride_kn=K.stride(2),
        stride_kd=K.stride(3),
        stride_vz=V.stride(0),
        stride_vh=V.stride(1),
        stride_vn=V.stride(2),
        stride_vd=V.stride(3),
        stride_mz=tmp_m.stride(0),
        stride_mh=tmp_m.stride(1),
        stride_mm=tmp_m.stride(2),
        stride_mb=tmp_m.stride(3),
        stride_lz=tmp_l.stride(0),
        stride_lh=tmp_l.stride(1),
        stride_lm=tmp_l.stride(2),
        stride_lb=tmp_l.stride(3),
        stride_az=tmp_a.stride(0),
        stride_ah=tmp_a.stride(1),
        stride_am=tmp_a.stride(2),
        stride_ab=tmp_a.stride(3),
        stride_ad=tmp_a.stride(4),
        H=H,
        Mq=Mq,
        DQ=DQ,
        DV=DV,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    grid2 = (Z * H * Mq,)
    _decoding_attn_stage2[grid2](
        tmp_m,
        tmp_l,
        tmp_a,
        out,
        stride_mz=tmp_m.stride(0),
        stride_mh=tmp_m.stride(1),
        stride_mm=tmp_m.stride(2),
        stride_mb=tmp_m.stride(3),
        stride_lz=tmp_l.stride(0),
        stride_lh=tmp_l.stride(1),
        stride_lm=tmp_l.stride(2),
        stride_lb=tmp_l.stride(3),
        stride_az=tmp_a.stride(0),
        stride_ah=tmp_a.stride(1),
        stride_am=tmp_a.stride(2),
        stride_ab=tmp_a.stride(3),
        stride_ad=tmp_a.stride(4),
        stride_oz=out.stride(0),
        stride_oh=out.stride(1),
        stride_om=out.stride(2),
        stride_od=out.stride(3),
        H=H,
        Mq=Mq,
        DV=DV,
        B=B,
        num_warps=4,
        num_stages=2,
    )

    return out.to(Q.dtype)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
