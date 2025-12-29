import os
import math
from typing import Optional, Dict

KERNEL_CODE = r"""
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 256}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=4),
    ],
    key=["N", "DQ", "DV"],
)
@triton.heuristics(
    {
        "EVEN_N": lambda args: (args["N"] % args["BLOCK_N"]) == 0,
    }
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    O_ptr,
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    Z: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    BLOCK_N: tl.constexpr,
    EVEN_N: tl.constexpr,
):
    pid = tl.program_id(0)
    hm = H * M
    z = pid // hm
    rm = pid - z * hm
    h = rm // M
    m = rm - h * M

    q_base = Q_ptr + z * stride_qz + h * stride_qh + m * stride_qm
    k_base = K_ptr + z * stride_kz + h * stride_kh
    v_base = V_ptr + z * stride_vz + h * stride_vh
    o_base = O_ptr + z * stride_oz + h * stride_oh + m * stride_om

    offs_dq = tl.arange(0, DQ)
    if tl.constexpr(DQ == 64):
        q = tl.load(q_base + offs_dq * stride_qd).to(tl.float16)
    else:
        q = tl.load(q_base + offs_dq * stride_qd, mask=offs_dq < DQ, other=0.0).to(tl.float16)
    qf = q.to(tl.float32)

    offs_dv = tl.arange(0, DV)
    m_i = tl.full((), -float("inf"), tl.float32)
    l_i = tl.zeros((), tl.float32)
    acc = tl.zeros((DV,), tl.float32)

    scale = 1.0 / math.sqrt(DQ)
    log2e = 1.4426950408889634

    if EVEN_N:
        for start_n in range(0, N, BLOCK_N):
            offs_n = start_n + tl.arange(0, BLOCK_N)

            k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
            k = tl.load(k_ptrs).to(tl.float16)
            s = tl.sum(k.to(tl.float32) * qf[None, :], axis=1) * scale

            m_new = tl.maximum(m_i, tl.max(s, axis=0))
            alpha = tl.exp2((m_i - m_new) * log2e)
            p = tl.exp2((s - m_new) * log2e)
            l_new = l_i * alpha + tl.sum(p, axis=0)

            v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs).to(tl.float16)
            pv = tl.dot(p.to(tl.float16)[None, :], v).to(tl.float32)
            acc = acc * alpha + pv[0, :]

            m_i = m_new
            l_i = l_new
    else:
        neg_inf = tl.full((), -float("inf"), tl.float32)
        for start_n in range(0, N, BLOCK_N):
            offs_n = start_n + tl.arange(0, BLOCK_N)
            mask_n = offs_n < N

            k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
            k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)
            s = tl.sum(k.to(tl.float32) * qf[None, :], axis=1) * scale
            s = tl.where(mask_n, s, neg_inf)

            m_new = tl.maximum(m_i, tl.max(s, axis=0))
            alpha = tl.exp2((m_i - m_new) * log2e)
            p = tl.exp2((s - m_new) * log2e)
            l_new = l_i * alpha + tl.sum(p, axis=0)

            v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)
            pv = tl.dot(p.to(tl.float16)[None, :], v).to(tl.float32)
            acc = acc * alpha + pv[0, :]

            m_i = m_new
            l_i = l_new

    inv_l = 1.0 / l_i
    out = (acc * inv_l).to(tl.float16)
    tl.store(o_base + offs_dv * stride_od, out, mask=offs_dv < DV)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Hk == H and DQk == DQ
    assert Zv == Z and Hv == H and Nv == N
    assert V.shape[-1] == DV

    if Q.dtype != torch.float16:
        Q = Q.to(torch.float16)
    if K.dtype != torch.float16:
        K = K.to(torch.float16)
    if V.dtype != torch.float16:
        V = V.to(torch.float16)

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    grid = (Z * H * M,)

    _decoding_attn_kernel[grid](
        Q,
        K,
        V,
        O,
        Q.stride(0),
        Q.stride(1),
        Q.stride(2),
        Q.stride(3),
        K.stride(0),
        K.stride(1),
        K.stride(2),
        K.stride(3),
        V.stride(0),
        V.stride(1),
        V.stride(2),
        V.stride(3),
        O.stride(0),
        O.stride(1),
        O.stride(2),
        O.stride(3),
        Z=Z,
        H=H,
        M=M,
        N=N,
        DQ=DQ,
        DV=DV,
    )
    return O
"""

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}