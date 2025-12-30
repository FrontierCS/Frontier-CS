import os
import math
from typing import Optional, Dict, Any


_KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

# ----------------------------- Kernels -----------------------------

@triton.jit
def _decoding_attn_block_kernel(
    Q_ptr, K_ptr, V_ptr,
    M_ptr, L_ptr, A_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_mq, stride_mb,
    stride_lq, stride_lb,
    stride_aq, stride_ab, stride_ad,
    Z: tl.constexpr,
    H: tl.constexpr,
    Mq: tl.constexpr,
    N: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_q = tl.program_id(0)
    pid_b = tl.program_id(1)

    hm = H * Mq
    z = pid_q // hm
    rem = pid_q - z * hm
    h = rem // Mq
    m = rem - h * Mq

    q_base = Q_ptr + z * stride_qz + h * stride_qh + m * stride_qm
    k_base = K_ptr + z * stride_kz + h * stride_kh
    v_base = V_ptr + z * stride_vz + h * stride_vh

    offs_dq = tl.arange(0, DQ)
    q = tl.load(q_base + offs_dq * stride_qd, mask=offs_dq < DQ, other=0.0).to(tl.float32)

    start_n = pid_b * BLOCK_N
    offs_n = start_n + tl.arange(0, BLOCK_N)
    n_mask = offs_n < N

    k_ptrs = k_base + (offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd)
    k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_dq[None, :] < DQ), other=0.0).to(tl.float32)

    scores = tl.sum(k * q[None, :], axis=1)
    scores = scores * (1.0 / math.sqrt(DQ))
    scores = tl.where(n_mask, scores, -float("inf"))

    m_i = tl.max(scores, axis=0)
    p = tl.exp(scores - m_i)
    l_i = tl.sum(p, axis=0)

    offs_dv = tl.arange(0, DV)
    v_ptrs = v_base + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
    v = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < DV), other=0.0).to(tl.float32)

    acc = tl.sum(v * p[:, None], axis=0)

    tl.store(M_ptr + pid_q * stride_mq + pid_b * stride_mb, m_i)
    tl.store(L_ptr + pid_q * stride_lq + pid_b * stride_lb, l_i)
    tl.store(A_ptr + pid_q * stride_aq + pid_b * stride_ab + offs_dv * stride_ad, acc, mask=offs_dv < DV)


@triton.jit
def _decoding_attn_reduce_kernel(
    M_ptr, L_ptr, A_ptr,
    Out_ptr,
    stride_mq, stride_mb,
    stride_lq, stride_lb,
    stride_aq, stride_ab, stride_ad,
    stride_oz, stride_oh, stride_om, stride_od,
    Z: tl.constexpr,
    H: tl.constexpr,
    Mq: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    NUM_BLOCKS: tl.constexpr,
):
    pid_q = tl.program_id(0)

    hm = H * Mq
    z = pid_q // hm
    rem = pid_q - z * hm
    h = rem // Mq
    m = rem - h * Mq

    offs_dv = tl.arange(0, DV)
    acc = tl.zeros([DV], dtype=tl.float32)

    m_global = -float("inf")
    for b in tl.static_range(0, NUM_BLOCKS):
        m_i = tl.load(M_ptr + pid_q * stride_mq + b * stride_mb)
        m_global = tl.maximum(m_global, m_i)

    l_global = 0.0
    for b in tl.static_range(0, NUM_BLOCKS):
        m_i = tl.load(M_ptr + pid_q * stride_mq + b * stride_mb)
        l_i = tl.load(L_ptr + pid_q * stride_lq + b * stride_lb)
        w = tl.exp(m_i - m_global)
        l_global += l_i * w

    for b in tl.static_range(0, NUM_BLOCKS):
        m_i = tl.load(M_ptr + pid_q * stride_mq + b * stride_mb)
        w = tl.exp(m_i - m_global)
        a_i = tl.load(A_ptr + pid_q * stride_aq + b * stride_ab + offs_dv * stride_ad, mask=offs_dv < DV, other=0.0).to(tl.float32)
        acc += a_i * w

    inv_l = tl.where(l_global > 0.0, 1.0 / l_global, 0.0)
    out = (acc * inv_l).to(tl.float16)

    out_ptrs = Out_ptr + z * stride_oz + h * stride_oh + m * stride_om + offs_dv * stride_od
    tl.store(out_ptrs, out, mask=offs_dv < DV)

# --------------------------- Python wrapper ---------------------------

_tmp_cache = {}

def _get_tmp_buffers(device, qcount: int, dv: int, nblocks: int):
    key = (device, qcount, dv)
    entry = _tmp_cache.get(key)
    if entry is None:
        nmax = nblocks
        m_buf = torch.empty((qcount, nmax), device=device, dtype=torch.float32)
        l_buf = torch.empty((qcount, nmax), device=device, dtype=torch.float32)
        a_buf = torch.empty((qcount, nmax, dv), device=device, dtype=torch.float32)
        _tmp_cache[key] = [nmax, m_buf, l_buf, a_buf]
        return m_buf, l_buf, a_buf

    nmax, m_buf, l_buf, a_buf = entry
    if nblocks > nmax:
        nmax = nblocks
        m_buf = torch.empty((qcount, nmax), device=device, dtype=torch.float32)
        l_buf = torch.empty((qcount, nmax), device=device, dtype=torch.float32)
        a_buf = torch.empty((qcount, nmax, dv), device=device, dtype=torch.float32)
        _tmp_cache[key] = [nmax, m_buf, l_buf, a_buf]
    return m_buf, l_buf, a_buf


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        raise ValueError("Q, K, V must be CUDA tensors")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16")
    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("Q, K, V must be 4D tensors")
    Z, H, Mq, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    if Zk != Z or Zv != Z or Hk != H or Hv != H or Nv != N or DQk != DQ:
        raise ValueError("Shape mismatch among Q, K, V")

    out = torch.empty((Z, H, Mq, DV), device=Q.device, dtype=torch.float16)

    if N == 0:
        out.zero_()
        return out

    # Heuristic block sizing
    if N <= 2048:
        BLOCK_N = 128
        num_warps = 4
    else:
        BLOCK_N = 256
        num_warps = 8

    nblocks = (N + BLOCK_N - 1) // BLOCK_N
    qcount = Z * H * Mq

    m_buf, l_buf, a_buf = _get_tmp_buffers(Q.device, qcount, DV, nblocks)

    grid_a = (qcount, nblocks)

    _decoding_attn_block_kernel[grid_a](
        Q, K, V,
        m_buf, l_buf, a_buf,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        m_buf.stride(0), m_buf.stride(1),
        l_buf.stride(0), l_buf.stride(1),
        a_buf.stride(0), a_buf.stride(1), a_buf.stride(2),
        Z=Z, H=H, Mq=Mq, N=N, DQ=DQ, DV=DV,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=2,
    )

    grid_b = (qcount,)

    _decoding_attn_reduce_kernel[grid_b](
        m_buf, l_buf, a_buf,
        out,
        m_buf.stride(0), m_buf.stride(1),
        l_buf.stride(0), l_buf.stride(1),
        a_buf.stride(0), a_buf.stride(1), a_buf.stride(2),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z=Z, H=H, Mq=Mq, DQ=DQ, DV=DV,
        NUM_BLOCKS=nblocks,
        num_warps=4,
        num_stages=1,
    )

    return out
'''


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        return {"code": _KERNEL_CODE}