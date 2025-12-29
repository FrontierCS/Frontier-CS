import os
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128}, num_warps=8, num_stages=4),
    ],
    key=[],
)
@triton.jit
def _gdpa_fwd_nomask(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqk,
    stride_gkz, stride_gkh, stride_gkn, stride_gkk,
    stride_oz, stride_oh, stride_om, stride_od,
    H: tl.constexpr,
    N: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    z = pid_bh // H
    h = pid_bh - z * H

    tl.multiple_of(stride_qm, 16)
    tl.multiple_of(stride_kn, 16)
    tl.multiple_of(stride_vn, 16)

    q_offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    q_offs_k = tl.arange(0, DQ)

    base_q = z * stride_qz + h * stride_qh
    base_k = z * stride_kz + h * stride_kh
    base_v = z * stride_vz + h * stride_vh
    base_gq = z * stride_gqz + h * stride_gqh
    base_gk = z * stride_gkz + h * stride_gkh
    base_o = z * stride_oz + h * stride_oh

    q_ptrs = Q_ptr + base_q + q_offs_m[:, None] * stride_qm + q_offs_k[None, :] * stride_qk
    gq_ptrs = GQ_ptr + base_gq + q_offs_m[:, None] * stride_gqm + q_offs_k[None, :] * stride_gqk

    q = tl.load(q_ptrs).to(tl.float16)
    gq = tl.load(gq_ptrs).to(tl.float16)
    q = q * tl.sigmoid(gq) * tl.full((), 0.125, tl.float16)

    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, DV), tl.float32)

    dv_offs = tl.arange(0, DV)

    for start_n in tl.static_range(0, N, BLOCK_N):
        n_offs = start_n + tl.arange(0, BLOCK_N)
        k_ptrs = K_ptr + base_k + n_offs[:, None] * stride_kn + q_offs_k[None, :] * stride_kk
        gk_ptrs = GK_ptr + base_gk + n_offs[:, None] * stride_gkn + q_offs_k[None, :] * stride_gkk
        v_ptrs = V_ptr + base_v + n_offs[:, None] * stride_vn + dv_offs[None, :] * stride_vd

        k = tl.load(k_ptrs).to(tl.float16)
        gk = tl.load(gk_ptrs).to(tl.float16)
        k = k * tl.sigmoid(gk)

        v = tl.load(v_ptrs).to(tl.float16)

        scores = tl.dot(q, tl.trans(k))
        m_ij = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new[:, None])
        l_new = l_i * alpha + tl.sum(p, axis=1)

        p16 = p.to(tl.float16)
        acc = acc * alpha[:, None] + tl.dot(p16, v)

        m_i = m_new
        l_i = l_new

    acc = acc / l_i[:, None]
    o_ptrs = O_ptr + base_o + q_offs_m[:, None] * stride_om + dv_offs[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16))


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Hk == H and Zv == Z and Hv == H
    assert N == Nv
    assert DQk == DQ
    assert GQ.shape == Q.shape
    assert GK.shape == K.shape

    if not (DQ == 64 and DV == 64 and M == N and (M % 128 == 0) and (N % 128 == 0)):
        scale = 1.0 / math.sqrt(DQ)
        Qg = Q * torch.sigmoid(GQ)
        Kg = K * torch.sigmoid(GK)
        attn = torch.softmax(torch.matmul(Qg, Kg.transpose(-1, -2)) * scale, dim=-1)
        return torch.matmul(attn, V).to(torch.float16)

    if not (Q.stride(-1) == 1 and K.stride(-1) == 1 and V.stride(-1) == 1 and GQ.stride(-1) == 1 and GK.stride(-1) == 1):
        scale = 1.0 / math.sqrt(DQ)
        Qg = Q * torch.sigmoid(GQ)
        Kg = K * torch.sigmoid(GK)
        attn = torch.softmax(torch.matmul(Qg, Kg.transpose(-1, -2)) * scale, dim=-1)
        return torch.matmul(attn, V).to(torch.float16)

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    sqz, sqh, sqm, sqk = Q.stride()
    skz, স্কh, skn, skk = K.stride()
    svz, svh, svn, svd = V.stride()
    sgqz, sgqh, sgqm, sgqk = GQ.stride()
    sgkz, sgkh, sgkn, sgkk = GK.stride()
    soz, soh, som, sod = O.stride()

    grid = lambda meta: (M // meta["BLOCK_M"], Z * H)

    _gdpa_fwd_nomask[grid](
        Q, K, V, GQ, GK, O,
        sqz, sqh, sqm, sqk,
        skz, স্কh, skn, skk,
        svz, svh, svn, svd,
        sgqz, sgqh, sgqm, sgqk,
        sgkz, sgkh, sgkn, sgkk,
        soz, soh, som, sod,
        H=H,
        N=N,
        DQ=64,
        DV=64,
    )
    return O


__all__ = ["gdpa_attn"]
'''
        code = textwrap.dedent(code).lstrip()
        return {"code": code}