import os
import math
import inspect
import sys
from typing import Optional, Dict

import torch

try:
    import triton
    import triton.language as tl
except Exception:  # pragma: no cover
    triton = None
    tl = None


if triton is not None:

    @triton.autotune(
        configs=[
            triton.Config({"BM": 64, "BN": 64}, num_warps=4, num_stages=4),
            triton.Config({"BM": 128, "BN": 64}, num_warps=8, num_stages=3),
            triton.Config({"BM": 64, "BN": 128}, num_warps=8, num_stages=3),
            triton.Config({"BM": 128, "BN": 128}, num_warps=8, num_stages=2),
        ],
        key=["N_CTX"],
    )
    @triton.jit
    def _gdpa_attn_fwd(
        Q_ptr,
        K_ptr,
        V_ptr,
        GQ_ptr,
        GK_ptr,
        O_ptr,
        stride_qh: tl.constexpr,
        stride_qm: tl.constexpr,
        stride_qk: tl.constexpr,
        stride_kh: tl.constexpr,
        stride_kn: tl.constexpr,
        stride_kk: tl.constexpr,
        stride_vh: tl.constexpr,
        stride_vn: tl.constexpr,
        stride_vk: tl.constexpr,
        stride_oh: tl.constexpr,
        stride_om: tl.constexpr,
        stride_ok: tl.constexpr,
        M_CTX: tl.constexpr,
        N_CTX: tl.constexpr,
        D: tl.constexpr,
        DV: tl.constexpr,
        SM_SCALE: tl.constexpr,
        BM: tl.constexpr,
        BN: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_b = tl.program_id(1)

        start_m = pid_m * BM
        offs_m = start_m + tl.arange(0, BM)
        offs_d = tl.arange(0, D)
        offs_dv = tl.arange(0, DV)

        q_base = Q_ptr + pid_b * stride_qh
        k_base = K_ptr + pid_b * stride_kh
        v_base = V_ptr + pid_b * stride_vh
        gq_base = GQ_ptr + pid_b * stride_qh
        gk_base = GK_ptr + pid_b * stride_kh
        o_base = O_ptr + pid_b * stride_oh

        q = tl.load(
            q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk,
            mask=(offs_m[:, None] < M_CTX),
            other=0.0,
        ).to(tl.float32)
        gq = tl.load(
            gq_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk,
            mask=(offs_m[:, None] < M_CTX),
            other=0.0,
        ).to(tl.float32)
        q = (q * tl.sigmoid(gq)).to(tl.float16)

        m_i = tl.full([BM], float("-inf"), tl.float32)
        l_i = tl.zeros([BM], tl.float32)
        acc = tl.zeros([BM, DV], tl.float32)

        for start_n in tl.static_range(0, N_CTX, BN):
            offs_n = start_n + tl.arange(0, BN)
            mask_n = offs_n < N_CTX

            k = tl.load(
                k_base + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kk,
                mask=(mask_n[None, :]),
                other=0.0,
            ).to(tl.float32)
            gk = tl.load(
                gk_base + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kk,
                mask=(mask_n[None, :]),
                other=0.0,
            ).to(tl.float32)
            k = (k * tl.sigmoid(gk)).to(tl.float16)

            scores = tl.dot(q, k) * SM_SCALE
            scores = tl.where(mask_n[None, :], scores, float("-inf"))

            m_ij = tl.maximum(m_i, tl.max(scores, axis=1))
            alpha = tl.exp(m_i - m_ij)

            p = tl.exp(scores - m_ij[:, None]).to(tl.float16)

            l_i = l_i * alpha + tl.sum(p.to(tl.float32), axis=1)

            v = tl.load(
                v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vk,
                mask=(mask_n[:, None]),
                other=0.0,
            ).to(tl.float16)

            acc = acc * alpha[:, None] + tl.dot(p, v, out_dtype=tl.float32)

            m_i = m_ij

        l_safe = tl.where(offs_m < M_CTX, l_i, 1.0)
        out = (acc / l_safe[:, None]).to(tl.float16)

        tl.store(
            o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ok,
            out,
            mask=(offs_m[:, None] < M_CTX),
        )


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if triton is None:
        qg = Q * torch.sigmoid(GQ)
        kg = K * torch.sigmoid(GK)
        attn = torch.matmul(qg, kg.transpose(-1, -2)) * (1.0 / math.sqrt(Q.shape[-1]))
        attn = torch.softmax(attn, dim=-1)
        out = torch.matmul(attn, V)
        return out.to(torch.float16)

    if not (Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16 or GQ.dtype != torch.float16 or GK.dtype != torch.float16:
        raise ValueError("All inputs must be torch.float16.")
    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4 or GQ.ndim != 4 or GK.ndim != 4:
        raise ValueError("All inputs must be rank-4 tensors.")
    if Q.shape[0] != K.shape[0] or Q.shape[0] != V.shape[0] or Q.shape[0] != GQ.shape[0] or Q.shape[0] != GK.shape[0]:
        raise ValueError("Batch dimension mismatch.")
    if Q.shape[1] != K.shape[1] or Q.shape[1] != V.shape[1] or Q.shape[1] != GQ.shape[1] or Q.shape[1] != GK.shape[1]:
        raise ValueError("Head dimension mismatch.")
    if Q.shape[2] != GQ.shape[2]:
        raise ValueError("Q and GQ sequence length mismatch.")
    if K.shape[2] != GK.shape[2]:
        raise ValueError("K and GK sequence length mismatch.")
    if Q.shape[2] != K.shape[2]:
        raise ValueError("This implementation assumes N == M.")
    if Q.shape[3] != K.shape[3] or Q.shape[3] != GQ.shape[3] or K.shape[3] != GK.shape[3]:
        raise ValueError("Dq dimension mismatch.")
    if Q.shape[3] != 64:
        raise ValueError("This implementation supports Dq=64 only.")
    if V.shape[3] != 64:
        raise ValueError("This implementation supports Dv=64 only.")

    Z, H, M, D = Q.shape
    N = K.shape[2]
    DV = V.shape[3]
    B = Z * H
    sm_scale = 1.0 / math.sqrt(D)

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()
    if not GQ.is_contiguous():
        GQ = GQ.contiguous()
    if not GK.is_contiguous():
        GK = GK.contiguous()

    Q2 = Q.reshape(B, M, D)
    K2 = K.reshape(B, N, D)
    V2 = V.reshape(B, N, DV)
    GQ2 = GQ.reshape(B, M, D)
    GK2 = GK.reshape(B, N, D)
    O2 = torch.empty((B, M, DV), device=Q.device, dtype=torch.float16)

    stride_qh, stride_qm, stride_qk = Q2.stride()
    stride_kh, stride_kn, stride_kk = K2.stride()
    stride_vh, stride_vn, stride_vk = V2.stride()
    stride_oh, stride_om, stride_ok = O2.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BM"]), B)

    _gdpa_attn_fwd[grid](
        Q2,
        K2,
        V2,
        GQ2,
        GK2,
        O2,
        stride_qh=stride_qh,
        stride_qm=stride_qm,
        stride_qk=stride_qk,
        stride_kh=stride_kh,
        stride_kn=stride_kn,
        stride_kk=stride_kk,
        stride_vh=stride_vh,
        stride_vn=stride_vn,
        stride_vk=stride_vk,
        stride_oh=stride_oh,
        stride_om=stride_om,
        stride_ok=stride_ok,
        M_CTX=M,
        N_CTX=N,
        D=D,
        DV=DV,
        SM_SCALE=sm_scale,
    )
    return O2.reshape(Z, H, M, DV)


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        try:
            path = os.path.abspath(__file__)
            return {"program_path": path}
        except Exception:
            code = inspect.getsource(sys.modules[__name__])
            return {"code": code}