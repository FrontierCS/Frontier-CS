import math
from typing import Dict, Optional


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = r'''
import math
import torch
try:
    import triton
    import triton.language as tl
    _TRITON_AVAILABLE = True
except Exception:
    _TRITON_AVAILABLE = False


if _TRITON_AVAILABLE:
    @triton.jit
    def _flash_attn_fwd(
        Q, K, V, Out, sm_scale,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        causal: tl.constexpr,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
        BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_zh = tl.program_id(1)
        z = pid_zh // H
        h = pid_zh % H

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        mask_m = offs_m < M

        offs_dq = tl.arange(0, BLOCK_DMODEL)
        offs_dv = tl.arange(0, BLOCK_DV)

        # Load Q tile [BLOCK_M, Dq]
        q_ptrs = Q + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=(mask_m[:, None] & (offs_dq[None, :] < Dq)), other=0.0)

        # Initialize streaming softmax variables
        m_i = tl.full((BLOCK_M,), -float('inf'), tl.float32)
        l_i = tl.zeros((BLOCK_M,), tl.float32)
        acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

        n_start = 0
        while n_start < N:
            offs_n = n_start + tl.arange(0, BLOCK_N)
            mask_n = offs_n < N

            # Load K [BLOCK_N, Dq] and V [BLOCK_N, Dv]
            k_ptrs = K + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
            k = tl.load(k_ptrs, mask=(mask_n[:, None] & (offs_dq[None, :] < Dq)), other=0.0)

            v_ptrs = V + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=(mask_n[:, None] & (offs_dv[None, :] < Dv)), other=0.0)

            # Compute attention scores S = Q @ K^T
            s = tl.dot(q, tl.trans(k))
            s = s * sm_scale

            # Build mask matrix [BLOCK_M, BLOCK_N]
            valid_mat = mask_m[:, None] & mask_n[None, :]
            if causal:
                row_idx = offs_m[:, None]
                col_idx = offs_n[None, :]
                causal_mat = row_idx >= col_idx
                valid_mat = valid_mat & causal_mat

            # Apply masking
            s = tl.where(valid_mat, s, float('-inf'))

            # Determine rows that have any valid columns in this block
            has_any_f = tl.max(tl.where(valid_mat, 1.0, 0.0), axis=1)
            row_has = has_any_f > 0.0

            # Compute new m_i
            s_max = tl.max(s, axis=1)
            m_i_new = tl.where(row_has, tl.maximum(m_i, s_max), m_i)

            # Compute p = exp(s - m_i_new) with masking
            p = tl.where(valid_mat, tl.exp(s - m_i_new[:, None]), 0.0)

            # Compute scaling factor for previous accumulator
            alpha = tl.where(row_has, tl.exp(m_i - m_i_new), 1.0)

            # Update l_i and acc
            l_i = l_i * alpha + tl.sum(p, axis=1)
            acc = acc * alpha[:, None] + tl.dot(p.to(tl.float32), v.to(tl.float32))

            # Update running max
            m_i = m_i_new

            n_start += BLOCK_N

        # Normalize
        out = acc / l_i[:, None]

        # Store
        o_ptrs = Out + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        out_mask = (mask_m[:, None] & (offs_dv[None, :] < Dv))
        tl.store(o_ptrs, out.to(tl.float16), mask=out_mask)


def _flash_attn_fallback(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    assert Dq == Dk
    Dv = V.shape[-1]
    sm_scale = 1.0 / math.sqrt(Dq)
    # Compute scores in float32 for stability
    scores = torch.matmul(Q.float(), K.transpose(-2, -1).float()) * sm_scale
    if causal:
        # Mask out upper triangle
        causal_mask = torch.triu(torch.ones((M, N), dtype=torch.bool, device=Q.device), diagonal=1)
        scores = scores.masked_fill(causal_mask, float('-inf'))
    P = torch.softmax(scores, dim=-1)
    out = torch.matmul(P, V.float()).to(torch.float16)
    return out


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.

    Args:
        Q: (Z, H, M, Dq) float16 CUDA
        K: (Z, H, N, Dq) float16 CUDA
        V: (Z, H, N, Dv) float16 CUDA
        causal: bool

    Returns:
        (Z, H, M, Dv) float16 CUDA
    """
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be on CUDA"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and Dq == Dk, "Shape mismatch among Q, K, V"
    if not _TRITON_AVAILABLE:
        return _flash_attn_fallback(Q, K, V, causal)

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    sm_scale = 1.0 / math.sqrt(Dq)

    # Tuned meta-parameters
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64  # assumes Dq <= 64 (typical); masked loads handle Dq < 64
    BLOCK_DV = 64      # assumes Dv <= 64 (typical); masked loads handle Dv < 64

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    _flash_attn_fwd[grid](
        Q, K, V, Out, sm_scale,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        causal=causal,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_warps=4, num_stages=2
    )

    return Out
'''
        return {"code": code}