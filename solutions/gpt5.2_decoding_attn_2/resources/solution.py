import math
import os
import textwrap
from typing import Dict, Tuple, Optional

import torch
import triton
import triton.language as tl


def _get_num_warps_for_block_n(block_n: int) -> int:
    if block_n >= 256:
        return 8
    if block_n >= 128:
        return 8
    return 4


_STAGE1_CONFIGS = [
    triton.Config({"BLOCK_N": 64}, num_warps=4, num_stages=2),
    triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
    triton.Config({"BLOCK_N": 128}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_N": 256}, num_warps=8, num_stages=3),
]


@triton.autotune(configs=_STAGE1_CONFIGS, key=["N_CTX", "DQ", "DV", "CHUNK_N"])
@triton.jit
def _decoding_attn_stage1(
    Q_ptr,
    K_ptr,
    V_ptr,
    M_ptr,
    L_ptr,
    A_ptr,
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
    stride_mc: tl.constexpr,
    stride_lz: tl.constexpr,
    stride_lh: tl.constexpr,
    stride_lm: tl.constexpr,
    stride_lc: tl.constexpr,
    stride_az: tl.constexpr,
    stride_ah: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ac: tl.constexpr,
    stride_ad: tl.constexpr,
    Z: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N_CTX: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    sm_scale: tl.constexpr,
    CHUNK_N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    NUM_CHUNKS: tl.constexpr = (N_CTX + CHUNK_N - 1) // CHUNK_N

    pid = tl.program_id(0)
    chunk_id = pid % NUM_CHUNKS
    qid = pid // NUM_CHUNKS

    m_id = qid % M
    qid = qid // M
    h_id = qid % H
    z_id = qid // H

    qd = tl.arange(0, DQ)
    q_ptrs = Q_ptr + z_id * stride_qz + h_id * stride_qh + m_id * stride_qm + qd * stride_qd
    q = tl.load(q_ptrs, mask=qd < DQ, other=0.0).to(tl.float32)

    m_i = tl.full((), -float("inf"), tl.float32)
    l_i = tl.full((), 0.0, tl.float32)
    dv = tl.arange(0, DV)
    acc = tl.zeros((DV,), tl.float32)

    chunk_start = chunk_id * CHUNK_N

    for offs in range(0, CHUNK_N, BLOCK_N):
        n = chunk_start + offs + tl.arange(0, BLOCK_N)
        n_mask = n < N_CTX

        k_ptrs = (
            K_ptr
            + z_id * stride_kz
            + h_id * stride_kh
            + n[:, None] * stride_kn
            + qd[None, :] * stride_kd
        )
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (qd[None, :] < DQ), other=0.0).to(tl.float32)
        scores = tl.sum(k * q[None, :], axis=1) * sm_scale
        scores = tl.where(n_mask, scores, -float("inf"))

        m_ij = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new)

        l_i = l_i * alpha + tl.sum(p, axis=0)

        v_ptrs = (
            V_ptr
            + z_id * stride_vz
            + h_id * stride_vh
            + n[:, None] * stride_vn
            + dv[None, :] * stride_vd
        )
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (dv[None, :] < DV), other=0.0).to(tl.float32)
        acc = acc * alpha + tl.sum(v * p[:, None], axis=0)

        m_i = m_new

    m_out_ptr = M_ptr + z_id * stride_mz + h_id * stride_mh + m_id * stride_mm + chunk_id * stride_mc
    l_out_ptr = L_ptr + z_id * stride_lz + h_id * stride_lh + m_id * stride_lm + chunk_id * stride_lc
    tl.store(m_out_ptr, m_i)
    tl.store(l_out_ptr, l_i)

    a_out_ptrs = (
        A_ptr
        + z_id * stride_az
        + h_id * stride_ah
        + m_id * stride_am
        + chunk_id * stride_ac
        + dv * stride_ad
    )
    tl.store(a_out_ptrs, acc.to(tl.float16), mask=dv < DV)


@triton.jit
def _decoding_attn_stage2(
    M_ptr,
    L_ptr,
    A_ptr,
    O_ptr,
    stride_mz: tl.constexpr,
    stride_mh: tl.constexpr,
    stride_mm: tl.constexpr,
    stride_mc: tl.constexpr,
    stride_lz: tl.constexpr,
    stride_lh: tl.constexpr,
    stride_lm: tl.constexpr,
    stride_lc: tl.constexpr,
    stride_az: tl.constexpr,
    stride_ah: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ac: tl.constexpr,
    stride_ad: tl.constexpr,
    stride_oz: tl.constexpr,
    stride_oh: tl.constexpr,
    stride_om: tl.constexpr,
    stride_od: tl.constexpr,
    Z: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N_CTX: tl.constexpr,
    DV: tl.constexpr,
    CHUNK_N: tl.constexpr,
):
    NUM_CHUNKS: tl.constexpr = (N_CTX + CHUNK_N - 1) // CHUNK_N

    pid = tl.program_id(0)
    m_id = pid % M
    pid2 = pid // M
    h_id = pid2 % H
    z_id = pid2 // H

    dv = tl.arange(0, DV)
    acc = tl.zeros((DV,), tl.float32)
    m_i = tl.full((), -float("inf"), tl.float32)
    l_i = tl.full((), 0.0, tl.float32)

    base_m = M_ptr + z_id * stride_mz + h_id * stride_mh + m_id * stride_mm
    base_l = L_ptr + z_id * stride_lz + h_id * stride_lh + m_id * stride_lm
    base_a = A_ptr + z_id * stride_az + h_id * stride_ah + m_id * stride_am

    for c in range(0, NUM_CHUNKS):
        m_c = tl.load(base_m + c * stride_mc).to(tl.float32)
        l_c = tl.load(base_l + c * stride_lc).to(tl.float32)

        a_ptrs = base_a + c * stride_ac + dv * stride_ad
        a_c = tl.load(a_ptrs, mask=dv < DV, other=0.0).to(tl.float32)

        m_new = tl.maximum(m_i, m_c)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_c - m_new)

        l_i = l_i * alpha + l_c * beta
        acc = acc * alpha + a_c * beta
        m_i = m_new

    l_i = tl.maximum(l_i, 1e-20)
    out = acc / l_i
    o_ptrs = O_ptr + z_id * stride_oz + h_id * stride_oh + m_id * stride_om + dv * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=dv < DV)


_temp_cache: Dict[Tuple[int, int, int, int, int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _get_temps(device: torch.device, Z: int, H: int, M: int, num_chunks: int, DV: int):
    key = (device.index if device.type == "cuda" else -1, Z, H, M, num_chunks, DV, 0)
    bufs = _temp_cache.get(key)
    if bufs is not None:
        m_buf, l_buf, a_buf = bufs
        if (
            m_buf.is_cuda
            and m_buf.device == device
            and m_buf.shape == (Z, H, M, num_chunks)
            and l_buf.shape == (Z, H, M, num_chunks)
            and a_buf.shape == (Z, H, M, num_chunks, DV)
        ):
            return bufs
    m_buf = torch.empty((Z, H, M, num_chunks), device=device, dtype=torch.float32)
    l_buf = torch.empty((Z, H, M, num_chunks), device=device, dtype=torch.float32)
    a_buf = torch.empty((Z, H, M, num_chunks, DV), device=device, dtype=torch.float16)
    _temp_cache[key] = (m_buf, l_buf, a_buf)
    return m_buf, l_buf, a_buf


@torch.no_grad()
def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and DQ == DQk
    assert DQ > 0 and DV > 0 and N > 0

    CHUNK_N = 256
    num_chunks = (N + CHUNK_N - 1) // CHUNK_N
    sm_scale = 1.0 / math.sqrt(DQ)

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)
    m_buf, l_buf, a_buf = _get_temps(Q.device, Z, H, M, num_chunks, DV)

    grid1 = (Z * H * M * num_chunks,)
    _decoding_attn_stage1[grid1](
        Q,
        K,
        V,
        m_buf,
        l_buf,
        a_buf,
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
        m_buf.stride(0),
        m_buf.stride(1),
        m_buf.stride(2),
        m_buf.stride(3),
        l_buf.stride(0),
        l_buf.stride(1),
        l_buf.stride(2),
        l_buf.stride(3),
        a_buf.stride(0),
        a_buf.stride(1),
        a_buf.stride(2),
        a_buf.stride(3),
        a_buf.stride(4),
        Z=Z,
        H=H,
        M=M,
        N_CTX=N,
        DQ=DQ,
        DV=DV,
        sm_scale=sm_scale,
        CHUNK_N=CHUNK_N,
    )

    grid2 = (Z * H * M,)
    _decoding_attn_stage2[grid2](
        m_buf,
        l_buf,
        a_buf,
        O,
        m_buf.stride(0),
        m_buf.stride(1),
        m_buf.stride(2),
        m_buf.stride(3),
        l_buf.stride(0),
        l_buf.stride(1),
        l_buf.stride(2),
        l_buf.stride(3),
        a_buf.stride(0),
        a_buf.stride(1),
        a_buf.stride(2),
        a_buf.stride(3),
        a_buf.stride(4),
        O.stride(0),
        O.stride(1),
        O.stride(2),
        O.stride(3),
        Z=Z,
        H=H,
        M=M,
        N_CTX=N,
        DV=DV,
        CHUNK_N=CHUNK_N,
        num_warps=4,
        num_stages=2,
    )
    return O


_KERNEL_CODE = textwrap.dedent(
    r"""
import math
from typing import Dict, Tuple

import torch
import triton
import triton.language as tl


_STAGE1_CONFIGS = [
    triton.Config({"BLOCK_N": 64}, num_warps=4, num_stages=2),
    triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
    triton.Config({"BLOCK_N": 128}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_N": 256}, num_warps=8, num_stages=3),
]


@triton.autotune(configs=_STAGE1_CONFIGS, key=["N_CTX", "DQ", "DV", "CHUNK_N"])
@triton.jit
def _decoding_attn_stage1(
    Q_ptr,
    K_ptr,
    V_ptr,
    M_ptr,
    L_ptr,
    A_ptr,
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
    stride_mc: tl.constexpr,
    stride_lz: tl.constexpr,
    stride_lh: tl.constexpr,
    stride_lm: tl.constexpr,
    stride_lc: tl.constexpr,
    stride_az: tl.constexpr,
    stride_ah: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ac: tl.constexpr,
    stride_ad: tl.constexpr,
    Z: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N_CTX: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    sm_scale: tl.constexpr,
    CHUNK_N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    NUM_CHUNKS: tl.constexpr = (N_CTX + CHUNK_N - 1) // CHUNK_N

    pid = tl.program_id(0)
    chunk_id = pid % NUM_CHUNKS
    qid = pid // NUM_CHUNKS

    m_id = qid % M
    qid = qid // M
    h_id = qid % H
    z_id = qid // H

    qd = tl.arange(0, DQ)
    q_ptrs = Q_ptr + z_id * stride_qz + h_id * stride_qh + m_id * stride_qm + qd * stride_qd
    q = tl.load(q_ptrs, mask=qd < DQ, other=0.0).to(tl.float32)

    m_i = tl.full((), -float("inf"), tl.float32)
    l_i = tl.full((), 0.0, tl.float32)
    dv = tl.arange(0, DV)
    acc = tl.zeros((DV,), tl.float32)

    chunk_start = chunk_id * CHUNK_N

    for offs in range(0, CHUNK_N, BLOCK_N):
        n = chunk_start + offs + tl.arange(0, BLOCK_N)
        n_mask = n < N_CTX

        k_ptrs = (
            K_ptr
            + z_id * stride_kz
            + h_id * stride_kh
            + n[:, None] * stride_kn
            + qd[None, :] * stride_kd
        )
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (qd[None, :] < DQ), other=0.0).to(tl.float32)
        scores = tl.sum(k * q[None, :], axis=1) * sm_scale
        scores = tl.where(n_mask, scores, -float("inf"))

        m_ij = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new)

        l_i = l_i * alpha + tl.sum(p, axis=0)

        v_ptrs = (
            V_ptr
            + z_id * stride_vz
            + h_id * stride_vh
            + n[:, None] * stride_vn
            + dv[None, :] * stride_vd
        )
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (dv[None, :] < DV), other=0.0).to(tl.float32)
        acc = acc * alpha + tl.sum(v * p[:, None], axis=0)

        m_i = m_new

    m_out_ptr = M_ptr + z_id * stride_mz + h_id * stride_mh + m_id * stride_mm + chunk_id * stride_mc
    l_out_ptr = L_ptr + z_id * stride_lz + h_id * stride_lh + m_id * stride_lm + chunk_id * stride_lc
    tl.store(m_out_ptr, m_i)
    tl.store(l_out_ptr, l_i)

    a_out_ptrs = (
        A_ptr
        + z_id * stride_az
        + h_id * stride_ah
        + m_id * stride_am
        + chunk_id * stride_ac
        + dv * stride_ad
    )
    tl.store(a_out_ptrs, acc.to(tl.float16), mask=dv < DV)


@triton.jit
def _decoding_attn_stage2(
    M_ptr,
    L_ptr,
    A_ptr,
    O_ptr,
    stride_mz: tl.constexpr,
    stride_mh: tl.constexpr,
    stride_mm: tl.constexpr,
    stride_mc: tl.constexpr,
    stride_lz: tl.constexpr,
    stride_lh: tl.constexpr,
    stride_lm: tl.constexpr,
    stride_lc: tl.constexpr,
    stride_az: tl.constexpr,
    stride_ah: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ac: tl.constexpr,
    stride_ad: tl.constexpr,
    stride_oz: tl.constexpr,
    stride_oh: tl.constexpr,
    stride_om: tl.constexpr,
    stride_od: tl.constexpr,
    Z: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N_CTX: tl.constexpr,
    DV: tl.constexpr,
    CHUNK_N: tl.constexpr,
):
    NUM_CHUNKS: tl.constexpr = (N_CTX + CHUNK_N - 1) // CHUNK_N

    pid = tl.program_id(0)
    m_id = pid % M
    pid2 = pid // M
    h_id = pid2 % H
    z_id = pid2 // H

    dv = tl.arange(0, DV)
    acc = tl.zeros((DV,), tl.float32)
    m_i = tl.full((), -float("inf"), tl.float32)
    l_i = tl.full((), 0.0, tl.float32)

    base_m = M_ptr + z_id * stride_mz + h_id * stride_mh + m_id * stride_mm
    base_l = L_ptr + z_id * stride_lz + h_id * stride_lh + m_id * stride_lm
    base_a = A_ptr + z_id * stride_az + h_id * stride_ah + m_id * stride_am

    for c in range(0, NUM_CHUNKS):
        m_c = tl.load(base_m + c * stride_mc).to(tl.float32)
        l_c = tl.load(base_l + c * stride_lc).to(tl.float32)

        a_ptrs = base_a + c * stride_ac + dv * stride_ad
        a_c = tl.load(a_ptrs, mask=dv < DV, other=0.0).to(tl.float32)

        m_new = tl.maximum(m_i, m_c)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_c - m_new)

        l_i = l_i * alpha + l_c * beta
        acc = acc * alpha + a_c * beta
        m_i = m_new

    l_i = tl.maximum(l_i, 1e-20)
    out = acc / l_i
    o_ptrs = O_ptr + z_id * stride_oz + h_id * stride_oh + m_id * stride_om + dv * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=dv < DV)


_temp_cache: Dict[Tuple[int, int, int, int, int, int], Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}


def _get_temps(device: torch.device, Z: int, H: int, M: int, num_chunks: int, DV: int):
    key = (device.index if device.type == "cuda" else -1, Z, H, M, num_chunks, DV)
    bufs = _temp_cache.get(key)
    if bufs is not None:
        m_buf, l_buf, a_buf = bufs
        if (
            m_buf.is_cuda
            and m_buf.device == device
            and m_buf.shape == (Z, H, M, num_chunks)
            and l_buf.shape == (Z, H, M, num_chunks)
            and a_buf.shape == (Z, H, M, num_chunks, DV)
        ):
            return bufs
    m_buf = torch.empty((Z, H, M, num_chunks), device=device, dtype=torch.float32)
    l_buf = torch.empty((Z, H, M, num_chunks), device=device, dtype=torch.float32)
    a_buf = torch.empty((Z, H, M, num_chunks, DV), device=device, dtype=torch.float16)
    _temp_cache[key] = (m_buf, l_buf, a_buf)
    return m_buf, l_buf, a_buf


@torch.no_grad()
def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and DQ == DQk
    assert DQ > 0 and DV > 0 and N > 0

    CHUNK_N = 256
    num_chunks = (N + CHUNK_N - 1) // CHUNK_N
    sm_scale = 1.0 / math.sqrt(DQ)

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)
    m_buf, l_buf, a_buf = _get_temps(Q.device, Z, H, M, num_chunks, DV)

    grid1 = (Z * H * M * num_chunks,)
    _decoding_attn_stage1[grid1](
        Q,
        K,
        V,
        m_buf,
        l_buf,
        a_buf,
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
        m_buf.stride(0),
        m_buf.stride(1),
        m_buf.stride(2),
        m_buf.stride(3),
        l_buf.stride(0),
        l_buf.stride(1),
        l_buf.stride(2),
        l_buf.stride(3),
        a_buf.stride(0),
        a_buf.stride(1),
        a_buf.stride(2),
        a_buf.stride(3),
        a_buf.stride(4),
        Z=Z,
        H=H,
        M=M,
        N_CTX=N,
        DQ=DQ,
        DV=DV,
        sm_scale=sm_scale,
        CHUNK_N=CHUNK_N,
    )

    grid2 = (Z * H * M,)
    _decoding_attn_stage2[grid2](
        m_buf,
        l_buf,
        a_buf,
        O,
        m_buf.stride(0),
        m_buf.stride(1),
        m_buf.stride(2),
        m_buf.stride(3),
        l_buf.stride(0),
        l_buf.stride(1),
        l_buf.stride(2),
        l_buf.stride(3),
        a_buf.stride(0),
        a_buf.stride(1),
        a_buf.stride(2),
        a_buf.stride(3),
        a_buf.stride(4),
        O.stride(0),
        O.stride(1),
        O.stride(2),
        O.stride(3),
        Z=Z,
        H=H,
        M=M,
        N_CTX=N,
        DV=DV,
        CHUNK_N=CHUNK_N,
        num_warps=4,
        num_stages=2,
    )
    return O
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}


__all__ = ["decoding_attn", "Solution"]
