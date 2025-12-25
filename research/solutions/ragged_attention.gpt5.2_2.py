import math
import os
from pathlib import Path
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    O_ptr,
    RL_ptr,
    M,
    stride_qm: tl.constexpr,
    stride_qd: tl.constexpr,
    stride_kn: tl.constexpr,
    stride_kd: tl.constexpr,
    stride_vn: tl.constexpr,
    stride_vd: tl.constexpr,
    stride_om: tl.constexpr,
    stride_od: tl.constexpr,
    SCALE: tl.constexpr,
    N: tl.constexpr,
    D: tl.constexpr,
    DV: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BM + tl.arange(0, BM)
    q_mask = offs_m < M

    rl = tl.load(RL_ptr + offs_m, mask=q_mask, other=0).to(tl.int32)
    row_active = q_mask & (rl > 0)

    offs_d = tl.arange(0, D)
    q = tl.load(
        Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
        mask=row_active[:, None],
        other=0.0,
    ).to(tl.float16)

    neg_inf = -1.0e9
    m = tl.where(row_active, tl.full([BM], neg_inf, tl.float32), tl.zeros([BM], tl.float32))
    l = tl.where(row_active, tl.zeros([BM], tl.float32), tl.ones([BM], tl.float32))
    acc = tl.zeros([BM, DV], tl.float32)

    offs_dv = tl.arange(0, DV)

    for n_start in tl.static_range(0, N, BN):
        offs_n = n_start + tl.arange(0, BN)
        n_in = offs_n < N

        k = tl.load(
            K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd,
            mask=n_in[:, None],
            other=0.0,
        ).to(tl.float16)

        scores = tl.dot(q, tl.trans(k)).to(tl.float32) * SCALE

        row_valid = row_active[:, None] & n_in[None, :] & (offs_n[None, :] < rl[:, None])
        scores = tl.where(row_valid, scores, neg_inf)

        max_score = tl.max(scores, axis=1)
        max_score = tl.where(row_active, max_score, 0.0)
        m_new = tl.maximum(m, max_score)
        m_new = tl.where(row_active, m_new, 0.0)

        alpha = tl.exp(m - m_new)
        alpha = tl.where(row_active, alpha, 1.0)

        p = tl.exp(scores - m_new[:, None])
        p = tl.where(row_valid, p, 0.0)
        p16 = p.to(tl.float16)

        v = tl.load(
            V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd,
            mask=n_in[:, None],
            other=0.0,
        ).to(tl.float16)

        acc = acc * alpha[:, None] + tl.dot(p16, v).to(tl.float32)
        l = l * alpha + tl.sum(p16.to(tl.float32), axis=1)

        m = m_new

    out = acc / l[:, None]
    out = out.to(tl.float16)

    tl.store(
        O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
        out,
        mask=q_mask[:, None],
    )


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda):
        D = Q.shape[1]
        scale = 1.0 / math.sqrt(D)
        N = K.shape[0]
        idx = torch.arange(N, device=Q.device)
        scores = (Q.float() @ K.float().T) * scale
        mask = idx[None, :] >= row_lens[:, None].to(idx.dtype)
        scores = scores.masked_fill(mask, float("-inf"))
        p = torch.softmax(scores, dim=1)
        out = p @ V.float()
        return out.to(torch.float16)

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2 and row_lens.ndim == 1
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert D == Dk
    assert N == Nv

    if D != 64 or DV != 64:
        scale = 1.0 / math.sqrt(D)
        idx = torch.arange(N, device=Q.device)
        scores = (Q.float() @ K.float().T) * scale
        mask = idx[None, :] >= row_lens[:, None].to(idx.dtype)
        scores = scores.masked_fill(mask, float("-inf"))
        p = torch.softmax(scores, dim=1)
        out = p @ V.float()
        return out.to(torch.float16)

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()
    if not row_lens.is_contiguous():
        row_lens = row_lens.contiguous()

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    BM = 16
    BN = 128
    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BM),)
    _ragged_attn_fwd_kernel[grid](
        Q,
        K,
        V,
        O,
        row_lens,
        M,
        stride_qm=Q.stride(0),
        stride_qd=Q.stride(1),
        stride_kn=K.stride(0),
        stride_kd=K.stride(1),
        stride_vn=V.stride(0),
        stride_vd=V.stride(1),
        stride_om=O.stride(0),
        stride_od=O.stride(1),
        SCALE=scale,
        N=N,
        D=64,
        DV=64,
        BM=BM,
        BN=BN,
        num_warps=4,
        num_stages=2,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            p = Path(__file__)
            return {"code": p.read_text()}
        except Exception:
            try:
                return {"program_path": os.path.abspath(__file__)}
            except Exception:
                return {"code": ""}