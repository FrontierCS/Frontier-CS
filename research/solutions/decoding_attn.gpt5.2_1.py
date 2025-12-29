import math
import os
import sys
from typing import Dict

KERNEL_SRC = r'''
import math
import torch
import triton
import triton.language as tl


def _ceil_pow2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()


def _pick_block_dim(x: int) -> int:
    b = _ceil_pow2(int(x))
    if b < 16:
        b = 16
    if b % 16 != 0:
        b = ((b + 15) // 16) * 16
    return b


def _pick_split(q: int, n: int) -> int:
    # Choose SPLIT from {1,2,4,8,16} to increase parallelism when q is small.
    if n <= 0:
        return 1
    if q <= 16:
        s = 16 if n >= 4096 else 8
    elif q <= 32:
        s = 8 if n >= 4096 else 4
    elif q <= 64:
        s = 4
    elif q <= 128:
        s = 2
    else:
        s = 1
    if s > 16:
        s = 16
    if s > n:
        # clamp to <= n but keep power-of-two
        s = 1 << ((n).bit_length() - 1)
        if s < 1:
            s = 1
    return int(s)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 256}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=4),
    ],
    key=["N", "DQ", "DV", "SPLIT", "CHUNK", "BLOCK_DQ", "BLOCK_DV"],
)
@triton.jit
def _decoding_attn_split_kernel(
    Q_ptr, K_ptr, V_ptr,
    TMP_M_ptr, TMP_L_ptr, TMP_A_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_tm_q: tl.constexpr, stride_tm_s: tl.constexpr,
    stride_tl_q: tl.constexpr, stride_tl_s: tl.constexpr,
    stride_ta_q: tl.constexpr, stride_ta_s: tl.constexpr, stride_ta_d: tl.constexpr,
    Z, H, M,
    N: tl.constexpr, DQ: tl.constexpr, DV: tl.constexpr,
    SPLIT: tl.constexpr,
    CHUNK: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DQ: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    SM_SCALE: tl.constexpr,
):
    pid_q = tl.program_id(0)
    pid_s = tl.program_id(1)

    hm = H * M
    z = pid_q // hm
    rem = pid_q - z * hm
    h = rem // M
    m = rem - h * M

    # load q
    offs_dq = tl.arange(0, BLOCK_DQ)
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + m * stride_qm + offs_dq * stride_qd
    q = tl.load(q_ptrs, mask=offs_dq < DQ, other=0.0).to(tl.float16)

    m_i = tl.full([1], -1.0e9, tl.float32)
    l_i = tl.zeros([1], tl.float32)
    acc = tl.zeros([BLOCK_DV], tl.float32)

    base_n = pid_s * CHUNK

    offs_dv = tl.arange(0, BLOCK_DV)

    for start in tl.static_range(0, CHUNK, BLOCK_N):
        offs_n = base_n + start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K block
        k_ptrs = K_ptr + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & (offs_dq[None, :] < DQ), other=0.0).to(tl.float16)

        # scores: (BLOCK_N,)
        s = tl.dot(k, q[:, None])[:, 0].to(tl.float32) * SM_SCALE
        s = tl.where(mask_n, s, -1.0e9)

        m_curr = tl.maximum(m_i, tl.max(s, axis=0))
        alpha = tl.exp(m_i - m_curr)

        p = tl.exp(s - m_curr)
        p = p * mask_n.to(tl.float32)

        l_curr = l_i * alpha + tl.sum(p, axis=0)

        # Load V block
        v_ptrs = V_ptr + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & (offs_dv[None, :] < DV), other=0.0).to(tl.float16)

        acc = acc * alpha + tl.dot(p.to(tl.float16)[None, :], v)[0, :].to(tl.float32)

        m_i = m_curr
        l_i = l_curr

    # Store partials
    tm_ptr = TMP_M_ptr + pid_q * stride_tm_q + pid_s * stride_tm_s
    tl_ptr = TMP_L_ptr + pid_q * stride_tl_q + pid_s * stride_tl_s
    tl.store(tm_ptr, m_i)
    tl.store(tl_ptr, l_i)

    ta_ptrs = TMP_A_ptr + pid_q * stride_ta_q + pid_s * stride_ta_s + offs_dv * stride_ta_d
    tl.store(ta_ptrs, acc, mask=offs_dv < DV)


@triton.jit
def _decoding_attn_reduce_kernel(
    TMP_M_ptr, TMP_L_ptr, TMP_A_ptr,
    O_ptr,
    stride_tm_q: tl.constexpr, stride_tm_s: tl.constexpr,
    stride_tl_q: tl.constexpr, stride_tl_s: tl.constexpr,
    stride_ta_q: tl.constexpr, stride_ta_s: tl.constexpr, stride_ta_d: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    Z, H, M,
    N: tl.constexpr,  # unused, but included for caching consistency
    DV: tl.constexpr,
    SPLIT: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_q = tl.program_id(0)

    hm = H * M
    z = pid_q // hm
    rem = pid_q - z * hm
    h = rem // M
    m = rem - h * M

    offs_s = tl.arange(0, SPLIT)
    m_s = tl.load(TMP_M_ptr + pid_q * stride_tm_q + offs_s * stride_tm_s).to(tl.float32)
    m_g = tl.max(m_s, axis=0)

    l_s = tl.load(TMP_L_ptr + pid_q * stride_tl_q + offs_s * stride_tl_s).to(tl.float32)
    scale_s = tl.exp(m_s - m_g)
    l_g = tl.sum(l_s * scale_s, axis=0)

    offs_dv = tl.arange(0, BLOCK_DV)
    a_ptrs = TMP_A_ptr + pid_q * stride_ta_q + offs_s[:, None] * stride_ta_s + offs_dv[None, :] * stride_ta_d
    a_s = tl.load(a_ptrs, mask=(offs_dv[None, :] < DV), other=0.0).to(tl.float32)
    acc = tl.sum(a_s * scale_s[:, None], axis=0)

    out = acc / l_g

    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + m * stride_om + offs_dv * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=offs_dv < DV)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        raise ValueError("Q, K, V must be CUDA tensors")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16 tensors")
    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("Q, K, V must be rank-4 tensors")
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    if Zk != Z or Zv != Z or Hk != H or Hv != H or DQk != DQ or Nv != N:
        raise ValueError("Shape mismatch: Q(Z,H,M,DQ), K(Z,H,N,DQ), V(Z,H,N,DV) required")

    q_count = int(Z * H * M)
    split = _pick_split(q_count, int(N))
    chunk = (int(N) + split - 1) // split

    block_dq = _pick_block_dim(int(DQ))
    block_dv = _pick_block_dim(int(DV))

    tmp_m = torch.empty((q_count, split), device=Q.device, dtype=torch.float32)
    tmp_l = torch.empty((q_count, split), device=Q.device, dtype=torch.float32)
    tmp_a = torch.empty((q_count, split, int(DV)), device=Q.device, dtype=torch.float32)
    O = torch.empty((int(Z), int(H), int(M), int(DV)), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()

    stride_tm_q, stride_tm_s = tmp_m.stride()
    stride_tl_q, stride_tl_s = tmp_l.stride()
    stride_ta_q, stride_ta_s, stride_ta_d = tmp_a.stride()

    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    sm_scale = 1.0 / math.sqrt(float(DQ))

    _decoding_attn_split_kernel[(q_count, split)](
        Q, K, V,
        tmp_m, tmp_l, tmp_a,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_tm_q, stride_tm_s,
        stride_tl_q, stride_tl_s,
        stride_ta_q, stride_ta_s, stride_ta_d,
        int(Z), int(H), int(M),
        N=int(N), DQ=int(DQ), DV=int(DV),
        SPLIT=int(split),
        CHUNK=int(chunk),
        BLOCK_DQ=int(block_dq),
        BLOCK_DV=int(block_dv),
        SM_SCALE=float(sm_scale),
    )

    _decoding_attn_reduce_kernel[(q_count,)](
        tmp_m, tmp_l, tmp_a,
        O,
        stride_tm_q, stride_tm_s,
        stride_tl_q, stride_tl_s,
        stride_ta_q, stride_ta_s, stride_ta_d,
        stride_oz, stride_oh, stride_om, stride_od,
        int(Z), int(H), int(M),
        N=int(N),
        DV=int(DV),
        SPLIT=int(split),
        BLOCK_DV=int(block_dv),
        num_warps=4,
        num_stages=2,
    )

    return O
'''

exec(KERNEL_SRC, globals())


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"code": KERNEL_SRC}