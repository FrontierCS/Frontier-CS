import os
import math
from typing import Dict, Optional, Tuple

import torch
import triton
import triton.language as tl


def _next_pow2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()


@triton.jit
def _decode_attn_stage1(
    Q_ptr, K_ptr, V_ptr,
    M_ptr, L_ptr, ACC_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr, M: tl.constexpr, N_CTX: tl.constexpr,
    sm_scale,
    BLOCK_N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
    SPLIT_K: tl.constexpr,
):
    pid_row = tl.program_id(0)
    pid_split = tl.program_id(1)

    m_idx = pid_row % M
    tmp = pid_row // M
    h_idx = tmp % H
    z_idx = tmp // H

    d_offsets = tl.arange(0, D)
    q_ptrs = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm + d_offsets * stride_qd
    q = tl.load(q_ptrs, mask=d_offsets < D, other=0.0).to(tl.float32)

    split_size = (N_CTX + SPLIT_K - 1) // SPLIT_K
    start_n = pid_split * split_size

    m_i = tl.full((), -1.0e20, tl.float32)
    l_i = tl.zeros((), tl.float32)
    acc = tl.zeros((DV,), tl.float32)

    dv_offsets = tl.arange(0, DV)

    for offs in tl.static_range(0, split_size, BLOCK_N):
        n_offsets = start_n + offs + tl.arange(0, BLOCK_N)
        n_mask = (n_offsets < N_CTX) & (n_offsets < start_n + split_size)

        k_ptrs = K_ptr + z_idx * stride_kz + h_idx * stride_kh + n_offsets[:, None] * stride_kn + d_offsets[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (d_offsets[None, :] < D), other=0.0).to(tl.float32)

        scores = tl.sum(k * q[None, :], axis=1) * sm_scale
        scores = tl.where(n_mask, scores, -1.0e20)

        m_b = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, m_b)
        alpha = tl.exp(m_i - m_new)

        p = tl.exp(scores - m_new)
        l_new = l_i * alpha + tl.sum(p, axis=0)

        v_ptrs = V_ptr + z_idx * stride_vz + h_idx * stride_vh + n_offsets[:, None] * stride_vn + dv_offsets[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (dv_offsets[None, :] < DV), other=0.0).to(tl.float32)

        acc = acc * alpha + tl.sum(v * p[:, None], axis=0)

        m_i = m_new
        l_i = l_new

    idx = pid_row * SPLIT_K + pid_split
    tl.store(M_ptr + idx, m_i)
    tl.store(L_ptr + idx, l_i)
    tl.store(ACC_ptr + idx * DV + dv_offsets, acc)


@triton.jit
def _decode_attn_stage2(
    M_ptr, L_ptr, ACC_ptr,
    Out_ptr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr, M: tl.constexpr,
    DV: tl.constexpr,
    SPLIT_K: tl.constexpr,
):
    pid_row = tl.program_id(0)

    m_idx = pid_row % M
    tmp = pid_row // M
    h_idx = tmp % H
    z_idx = tmp // H

    s_offsets = tl.arange(0, SPLIT_K)
    m_vec = tl.load(M_ptr + pid_row * SPLIT_K + s_offsets).to(tl.float32)
    m = tl.max(m_vec, axis=0)

    w = tl.exp(m_vec - m)
    l_vec = tl.load(L_ptr + pid_row * SPLIT_K + s_offsets).to(tl.float32)
    l = tl.sum(l_vec * w, axis=0)
    l = tl.maximum(l, 1.0e-20)

    dv_offsets = tl.arange(0, DV)
    acc_ptrs = ACC_ptr + (pid_row * SPLIT_K + s_offsets)[:, None] * DV + dv_offsets[None, :]
    acc_mat = tl.load(acc_ptrs).to(tl.float32)
    acc = tl.sum(acc_mat * w[:, None], axis=0)

    out = acc / l
    out_ptrs = Out_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om + dv_offsets * stride_od
    tl.store(out_ptrs, out.to(tl.float16), mask=dv_offsets < DV)


_TEMP_CACHE: Dict[Tuple[int, int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _get_temps(device: torch.device, rows: int, split_k: int, dv: int):
    key = (device.index if device.type == "cuda" else -1, rows, split_k, dv)
    t = _TEMP_CACHE.get(key, None)
    if t is None or any(x is None for x in t):
        m = torch.empty((rows * split_k,), device=device, dtype=torch.float32)
        l = torch.empty((rows * split_k,), device=device, dtype=torch.float32)
        acc = torch.empty((rows * split_k * dv,), device=device, dtype=torch.float32)
        _TEMP_CACHE[key] = (m, l, acc)
        return m, l, acc
    m, l, acc = t
    if m.numel() != rows * split_k or l.numel() != rows * split_k or acc.numel() != rows * split_k * dv:
        m = torch.empty((rows * split_k,), device=device, dtype=torch.float32)
        l = torch.empty((rows * split_k,), device=device, dtype=torch.float32)
        acc = torch.empty((rows * split_k * dv,), device=device, dtype=torch.float32)
        _TEMP_CACHE[key] = (m, l, acc)
    return _TEMP_CACHE[key]


def _pick_meta(Z: int, H: int, M: int, N: int) -> Tuple[int, int, int, int]:
    rows = Z * H * M
    block_n = 256 if N >= 2048 else 128
    max_split = max(1, N // block_n)
    desired_blocks = 256
    split_needed = (desired_blocks + rows - 1) // rows
    split = _next_pow2(split_needed)
    split = min(split, 32)
    split = min(split, max_split)
    if split < 1:
        split = 1
    num_warps = 8 if block_n == 256 else 4
    num_stages = 2
    return block_n, split, num_warps, num_stages


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        # CPU fallback
        D = Q.shape[-1]
        sm_scale = 1.0 / math.sqrt(D)
        att = torch.matmul(Q.float(), K.float().transpose(-2, -1)) * sm_scale
        att = torch.softmax(att, dim=-1)
        out = torch.matmul(att, V.float())
        return out.to(torch.float16)

    if Q.dtype not in (torch.float16, torch.bfloat16):
        Q = Q.to(torch.float16)
    if K.dtype not in (torch.float16, torch.bfloat16):
        K = K.to(torch.float16)
    if V.dtype not in (torch.float16, torch.bfloat16):
        V = V.to(torch.float16)

    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, Mq, D = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and D == Dk and Mq >= 1

    device = Q.device
    out = torch.empty((Z, H, Mq, DV), device=device, dtype=torch.float16)

    rows = Z * H * Mq
    block_n, split_k, num_warps, num_stages = _pick_meta(Z, H, Mq, N)

    m_buf, l_buf, acc_buf = _get_temps(device, rows, split_k, DV)

    sm_scale = 1.0 / math.sqrt(D)

    grid1 = (rows, split_k)
    _decode_attn_stage1[grid1](
        Q, K, V,
        m_buf, l_buf, acc_buf,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Z=Z, H=H, M=Mq, N_CTX=N,
        sm_scale=sm_scale,
        BLOCK_N=block_n, D=D, DV=DV, SPLIT_K=split_k,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    grid2 = (rows,)
    _decode_attn_stage2[grid2](
        m_buf, l_buf, acc_buf,
        out,
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z=Z, H=H, M=Mq,
        DV=DV,
        SPLIT_K=split_k,
        num_warps=4,
        num_stages=1,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}