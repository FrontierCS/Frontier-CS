import math
import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64,  'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64,  'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64,  'BLOCK_DQ': 64,  'BLOCK_DV': 128}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 128}, num_warps=4, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Load Q tile: [BM, Dq]
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q_mask = (offs_m[:, None] < M) & (offs_dq[None, :] < Dq)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # Online softmax state per row in BM
    m_i = tl.full((BLOCK_M,), -float('inf'), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    # Loop over K/V blocks along N
    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K block: [BN, Dq]
        k_ptrs = K_ptr + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=(n_mask[:, None] & (offs_dq[None, :] < Dq)), other=0.0)

        # Compute qk: [BM, BN]
        qk = tl.dot(q, tl.trans(k)).to(tl.float32)
        qk = qk * sm_scale
        qk = tl.where(n_mask[None, :], qk, -float('inf'))

        # Compute new max and l values
        m_curr = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_curr)

        p = tl.exp(qk - m_new[:, None])
        l_new = tl.exp(m_i - m_new) * l_i + tl.sum(p, axis=1)

        # Load V block: [BN, Dv]
        v_ptrs = V_ptr + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=(n_mask[:, None] & (offs_dv[None, :] < Dv)), other=0.0).to(tl.float32)

        # Update accumulator
        acc = acc * (tl.exp(m_i - m_new))[:, None] + tl.dot(p.to(tl.float32), v)

        # Commit state
        m_i = m_new
        l_i = l_new

        start_n += BLOCK_N

    # Normalize and store
    out = acc / l_i[:, None]
    out = out.to(tl.float16)
    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, out, mask=o_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        # Fallback to PyTorch on CPU if needed
        sm_scale = 1.0 / math.sqrt(Q.shape[-1])
        attn = torch.softmax(torch.matmul(Q.to(torch.float32), K.transpose(-1, -2).to(torch.float32)) * sm_scale, dim=-1)
        O = torch.matmul(attn, V.to(torch.float32)).to(Q.dtype)
        return O

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "decoding_attn expects fp16 inputs"
    assert Q.device.type == 'cuda' and K.device.type == 'cuda' and V.device.type == 'cuda'
    assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch (Z) mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1], "Head (H) mismatch"
    assert Q.shape[-1] == K.shape[-1], "Dq mismatch between Q and K"

    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape

    sm_scale = 1.0 / math.sqrt(Dq)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    # Pick BLOCK sizes as next power of two to cover D dimensions
    def next_power_of_2(x):
        return 1 if x <= 1 else 1 << (x - 1).bit_length()

    BLOCK_DQ = next_power_of_2(int(Dq))
    BLOCK_DV = next_power_of__2(int(Dv))

    # Reasonable caps to avoid too large tiles
    BLOCK_DQ = 128 if BLOCK_DQ > 128 else BLOCK_DQ
    BLOCK_DV = 128 if BLOCK_DV > 128 else BLOCK_DV

    grid = (Z * H, triton.cdiv(M, 1))
    # Kernel launch
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        BLOCK_M=1,  # decoding typically M=1; kernel still supports >1 for small blocks
        BLOCK_N=0,  # Will be set by autotuner
        BLOCK_DQ=BLOCK_DQ,
        BLOCK_DV=BLOCK_DV,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64,  'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64,  'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64,  'BLOCK_DQ': 64,  'BLOCK_DV': 128}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 128}, num_warps=4, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Load Q tile: [BM, Dq]
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q_mask = (offs_m[:, None] < M) & (offs_dq[None, :] < Dq)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # Online softmax state per row in BM
    m_i = tl.full((BLOCK_M,), -float('inf'), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    # Loop over K/V blocks along N
    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K block: [BN, Dq]
        k_ptrs = K_ptr + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=(n_mask[:, None] & (offs_dq[None, :] < Dq)), other=0.0)

        # Compute qk: [BM, BN]
        qk = tl.dot(q, tl.trans(k)).to(tl.float32)
        qk = qk * sm_scale
        qk = tl.where(n_mask[None, :], qk, -float('inf'))

        # Compute new max and l values
        m_curr = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_curr)

        p = tl.exp(qk - m_new[:, None])
        l_new = tl.exp(m_i - m_new) * l_i + tl.sum(p, axis=1)

        # Load V block: [BN, Dv]
        v_ptrs = V_ptr + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=(n_mask[:, None] & (offs_dv[None, :] < Dv)), other=0.0).to(tl.float32)

        # Update accumulator
        acc = acc * (tl.exp(m_i - m_new))[:, None] + tl.dot(p.to(tl.float32), v)

        # Commit state
        m_i = m_new
        l_i = l_new

        start_n += BLOCK_N

    # Normalize and store
    out = acc / l_i[:, None]
    out = out.to(tl.float16)
    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, out, mask=o_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        # Fallback to PyTorch on CPU if needed
        sm_scale = 1.0 / math.sqrt(Q.shape[-1])
        attn = torch.softmax(torch.matmul(Q.to(torch.float32), K.transpose(-1, -2).to(torch.float32)) * sm_scale, dim=-1)
        O = torch.matmul(attn, V.to(torch.float32)).to(Q.dtype)
        return O

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "decoding_attn expects fp16 inputs"
    assert Q.device.type == 'cuda' and K.device.type == 'cuda' and V.device.type == 'cuda'
    assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch (Z) mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1], "Head (H) mismatch"
    assert Q.shape[-1] == K.shape[-1], "Dq mismatch between Q and K"

    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape

    sm_scale = 1.0 / math.sqrt(Dq)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    def next_power_of_2(x):
        return 1 if x <= 1 else 1 << (x - 1).bit_length()

    BLOCK_DQ = next_power_of_2(int(Dq))
    BLOCK_DV = next_power_of_2(int(Dv))
    BLOCK_DQ = 128 if BLOCK_DQ > 128 else BLOCK_DQ
    BLOCK_DV = 128 if BLOCK_DV > 128 else BLOCK_DV

    grid = (Z * H, triton.cdiv(M, 1))
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        BLOCK_M=1,
        BLOCK_N=0,  # autotuner
        BLOCK_DQ=BLOCK_DQ,
        BLOCK_DV=BLOCK_DV,
    )
    return O
"""
        return {"code": code}
