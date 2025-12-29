from typing import Dict, Optional


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd(
    Q, K, V, ROW_LENS, O,
    M, N,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, BLOCK_DMODEL)
    mask_d = offs_d < D

    # Load row lengths
    row_lens_ptrs = ROW_LENS + offs_m
    row_lens_i = tl.load(row_lens_ptrs, mask=mask_m, other=0).to(tl.int32)

    has_len = mask_m & (row_lens_i > 0)

    # Load Q
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    q = q.to(tl.float32)

    scale = 1.0 / tl.sqrt(tl.float32(D))

    NEG_INF = -1.0e9

    m_i = tl.where(
        has_len,
        tl.full((BLOCK_M,), NEG_INF, tl.float32),
        tl.zeros((BLOCK_M,), tl.float32),
    )
    l_i = tl.where(
        has_len,
        tl.zeros((BLOCK_M,), tl.float32),
        tl.ones((BLOCK_M,), tl.float32),
    )

    offs_v = tl.arange(0, BLOCK_DV)
    mask_v = offs_v < Dv

    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K
        k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        k = k.to(tl.float32)

        # Load V
        v_ptrs = V + offs_n[:, None] * stride_vm + offs_v[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_v[None, :], other=0.0)
        v = v.to(tl.float32)

        # Compute QK^T
        qk = tl.dot(q, k, trans_b=True)
        qk = qk * scale

        # Apply ragged mask
        row_lens_broadcast = row_lens_i[:, None]
        offs_n_broadcast = offs_n[None, :]
        mask_len = offs_n_broadcast < row_lens_broadcast
        attn_mask = has_len[:, None] & mask_n[None, :] & mask_len

        qk = tl.where(attn_mask, qk, NEG_INF)

        # Streaming softmax update
        qk_max = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, qk_max)

        p = tl.exp(qk - m_i_new[:, None])

        p_sum = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - m_i_new)

        l_i = l_i * alpha + p_sum

        pv = tl.dot(p, v)
        acc = acc * alpha[:, None] + pv

        m_i = m_i_new

        start_n += BLOCK_N

    acc = acc / l_i[:, None]

    # Store result
    o_ptrs = O + offs_m[:, None] * stride_om + offs_v[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_v[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """Ragged attention computation.

    Args:
        Q: (M, D) float16 CUDA tensor
        K: (N, D) float16 CUDA tensor
        V: (N, Dv) float16 CUDA tensor
        row_lens: (M,) int32/int64 CUDA tensor
    Returns:
        (M, Dv) float16 CUDA tensor
    """
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda):
        raise ValueError("All tensors must be CUDA tensors")

    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise TypeError("Q, K, V must be float16 tensors")

    row_lens_i32 = row_lens.to(device=Q.device, dtype=torch.int32).contiguous()

    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape

    if N != N_v:
        raise ValueError("K and V must have the same leading dimension")

    if D != D_k:
        raise ValueError("Q and K must have the same feature dimension")

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_fwd[grid](
        Q, K, V, row_lens_i32, O,
        M, N,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        D, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O
'''
        return {"code": code}