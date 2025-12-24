import math
import os
import textwrap
from typing import Dict, Optional

import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.jit
    def _flash_attn_fwd_kernel(
        Q_ptr,
        K_ptr,
        V_ptr,
        O_ptr,
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
        stride_oz: tl.constexpr,
        stride_oh: tl.constexpr,
        stride_om: tl.constexpr,
        stride_od: tl.constexpr,
        H: tl.constexpr,
        M_CTX: tl.constexpr,
        N_CTX: tl.constexpr,
        D_HEAD: tl.constexpr,
        D_V: tl.constexpr,
        SM_SCALE: tl.constexpr,
        CAUSAL: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_bh = tl.program_id(1)

        z = pid_bh // H
        h = pid_bh - z * H

        start_m = pid_m * BLOCK_M
        offs_m = start_m + tl.arange(0, BLOCK_M)
        m_mask = offs_m < M_CTX

        offs_d = tl.arange(0, D_HEAD)
        q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float16)

        m_i = tl.full([BLOCK_M], -1.0e9, tl.float32)
        l_i = tl.zeros([BLOCK_M], tl.float32)
        acc = tl.zeros([BLOCK_M, D_V], tl.float32)

        offs_dv = tl.arange(0, D_V)

        for start_n in tl.static_range(0, N_CTX, BLOCK_N):
            offs_n = start_n + tl.arange(0, BLOCK_N)
            n_mask = offs_n < N_CTX

            k_ptrs = K_ptr + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
            k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

            v_ptrs = V_ptr + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

            scores = tl.dot(q, tl.trans(k)).to(tl.float32) * SM_SCALE
            scores = tl.where(n_mask[None, :], scores, -1.0e9)

            if CAUSAL:
                causal_mask = offs_m[:, None] < offs_n[None, :]
                scores = tl.where(causal_mask, -1.0e9, scores)

            scores = tl.where(m_mask[:, None], scores, -1.0e9)

            m_ij = tl.max(scores, axis=1)
            m_i_new = tl.maximum(m_i, m_ij)
            m_i_new = tl.where(m_mask, m_i_new, 0.0)

            alpha = tl.exp(m_i - m_i_new)
            alpha = tl.where(m_mask, alpha, 0.0)

            p = tl.exp(scores - m_i_new[:, None])
            p = tl.where(m_mask[:, None], p, 0.0)

            l_i = alpha * l_i + tl.sum(p, axis=1)
            acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)

            m_i = m_i_new

        l_i_safe = tl.where(m_mask, l_i, 1.0)
        out = acc / l_i_safe[:, None]

        o_ptrs = O_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    if triton is None:
        raise RuntimeError("Triton is required but not available.")

    if Q.device.type != "cuda" or K.device.type != "cuda" or V.device.type != "cuda":
        raise ValueError("Q, K, V must be CUDA tensors.")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16.")

    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("Q, K, V must have shape (Z, H, M/N, D).")

    Zq, Hq, M, D = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    if Zq != Zk or Zq != Zv or Hq != Hk or Hq != Hv:
        raise ValueError("Batch/head dims must match across Q, K, V.")
    if D != Dk:
        raise ValueError("Q and K head dimensions must match.")
    if N != Nv:
        raise ValueError("K and V sequence lengths must match.")

    if M == 0 or N == 0:
        return torch.empty((Zq, Hq, M, Dv), device=Q.device, dtype=torch.float16)

    sm_scale = 1.0 / math.sqrt(D)

    if causal:
        BLOCK_M = 128
        BLOCK_N = 64
        num_warps = 4
        num_stages = 4
    else:
        if N >= 1024:
            BLOCK_M = 128
            BLOCK_N = 128
            num_warps = 8
            num_stages = 4
        else:
            BLOCK_M = 128
            BLOCK_N = 64
            num_warps = 4
            num_stages = 3

    O = torch.empty((Zq, Hq, M, Dv), device=Q.device, dtype=torch.float16)

    grid = (triton.cdiv(M, BLOCK_M), Zq * Hq)

    _flash_attn_fwd_kernel[grid](
        Q,
        K,
        V,
        O,
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
        stride_oz=O.stride(0),
        stride_oh=O.stride(1),
        stride_om=O.stride(2),
        stride_od=O.stride(3),
        H=Hq,
        M_CTX=M,
        N_CTX=N,
        D_HEAD=D,
        D_V=Dv,
        SM_SCALE=sm_scale,
        CAUSAL=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _flash_attn_fwd_kernel(
                Q_ptr,
                K_ptr,
                V_ptr,
                O_ptr,
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
                stride_oz: tl.constexpr,
                stride_oh: tl.constexpr,
                stride_om: tl.constexpr,
                stride_od: tl.constexpr,
                H: tl.constexpr,
                M_CTX: tl.constexpr,
                N_CTX: tl.constexpr,
                D_HEAD: tl.constexpr,
                D_V: tl.constexpr,
                SM_SCALE: tl.constexpr,
                CAUSAL: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_bh = tl.program_id(1)

                z = pid_bh // H
                h = pid_bh - z * H

                start_m = pid_m * BLOCK_M
                offs_m = start_m + tl.arange(0, BLOCK_M)
                m_mask = offs_m < M_CTX

                offs_d = tl.arange(0, D_HEAD)
                q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float16)

                m_i = tl.full([BLOCK_M], -1.0e9, tl.float32)
                l_i = tl.zeros([BLOCK_M], tl.float32)
                acc = tl.zeros([BLOCK_M, D_V], tl.float32)

                offs_dv = tl.arange(0, D_V)

                for start_n in tl.static_range(0, N_CTX, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    n_mask = offs_n < N_CTX

                    k_ptrs = K_ptr + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
                    k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

                    v_ptrs = V_ptr + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

                    scores = tl.dot(q, tl.trans(k)).to(tl.float32) * SM_SCALE
                    scores = tl.where(n_mask[None, :], scores, -1.0e9)

                    if CAUSAL:
                        causal_mask = offs_m[:, None] < offs_n[None, :]
                        scores = tl.where(causal_mask, -1.0e9, scores)

                    scores = tl.where(m_mask[:, None], scores, -1.0e9)

                    m_ij = tl.max(scores, axis=1)
                    m_i_new = tl.maximum(m_i, m_ij)
                    m_i_new = tl.where(m_mask, m_i_new, 0.0)

                    alpha = tl.exp(m_i - m_i_new)
                    alpha = tl.where(m_mask, alpha, 0.0)

                    p = tl.exp(scores - m_i_new[:, None])
                    p = tl.where(m_mask[:, None], p, 0.0)

                    l_i = alpha * l_i + tl.sum(p, axis=1)
                    acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)

                    m_i = m_i_new

                l_i_safe = tl.where(m_mask, l_i, 1.0)
                out = acc / l_i_safe[:, None]

                o_ptrs = O_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])


            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                if Q.device.type != "cuda" or K.device.type != "cuda" or V.device.type != "cuda":
                    raise ValueError("Q, K, V must be CUDA tensors.")
                if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
                    raise ValueError("Q, K, V must be float16.")
                if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
                    raise ValueError("Q, K, V must have shape (Z, H, M/N, D).")

                Zq, Hq, M, D = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape
                if Zq != Zk or Zq != Zv or Hq != Hk or Hq != Hv:
                    raise ValueError("Batch/head dims must match across Q, K, V.")
                if D != Dk:
                    raise ValueError("Q and K head dimensions must match.")
                if N != Nv:
                    raise ValueError("K and V sequence lengths must match.")

                if M == 0 or N == 0:
                    return torch.empty((Zq, Hq, M, Dv), device=Q.device, dtype=torch.float16)

                sm_scale = 1.0 / math.sqrt(D)

                if causal:
                    BLOCK_M = 128
                    BLOCK_N = 64
                    num_warps = 4
                    num_stages = 4
                else:
                    if N >= 1024:
                        BLOCK_M = 128
                        BLOCK_N = 128
                        num_warps = 8
                        num_stages = 4
                    else:
                        BLOCK_M = 128
                        BLOCK_N = 64
                        num_warps = 4
                        num_stages = 3

                O = torch.empty((Zq, Hq, M, Dv), device=Q.device, dtype=torch.float16)
                grid = (triton.cdiv(M, BLOCK_M), Zq * Hq)

                _flash_attn_fwd_kernel[grid](
                    Q,
                    K,
                    V,
                    O,
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
                    stride_oz=O.stride(0),
                    stride_oh=O.stride(1),
                    stride_om=O.stride(2),
                    stride_od=O.stride(3),
                    H=Hq,
                    M_CTX=M,
                    N_CTX=N,
                    D_HEAD=D,
                    D_V=Dv,
                    SM_SCALE=sm_scale,
                    CAUSAL=causal,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )
                return O
            """
        ).strip()
        return {"code": code}
