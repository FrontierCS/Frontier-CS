import torch
import triton
import triton.language as tl
import math
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
import math


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 256}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 256}, num_warps=8, num_stages=3),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale,
    D_HEAD_Q: tl.constexpr, D_HEAD_V: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)

    h = pid_zh % H
    z = pid_zh // H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, D_HEAD_Q)
    offs_dv = tl.arange(0, D_HEAD_V)

    # Pointers for Q [BLOCK_M, D_HEAD_Q]
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh \
             + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q_mask = (offs_m[:, None] < M)

    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # init online softmax state
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_HEAD_V), dtype=tl.float32)

    n_start = 0
    while n_start < N:
        n_idx = n_start + offs_n
        k_ptrs = K_ptr + z * stride_kz + h * stride_kh \
                 + n_idx[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = V_ptr + z * stride_vz + h * stride_vh \
                 + n_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k_mask = (n_idx[:, None] < N)
        v_mask = (n_idx[:, None] < N)

        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)   # [BLOCK_N, D_HEAD_Q]
        # scores: [BLOCK_M, BLOCK_N]
        scores = tl.dot(q, tl.trans(k)) * sm_scale

        # mask scores for out-of-bounds n
        valid_n = (n_idx < N)[None, :]
        scores = tl.where(valid_n, scores, -float('inf'))

        m_ij = tl.max(scores, axis=1)
        p = tl.exp(scores - m_ij[:, None])
        l_ij = tl.sum(p, axis=1)

        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float32)   # [BLOCK_N, D_HEAD_V]
        acc_ij = tl.dot(p, v)  # [BLOCK_M, D_HEAD_V]

        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)

        l_i = alpha * l_i + beta * l_ij
        acc = alpha[:, None] * acc + beta[:, None] * acc_ij
        m_i = m_new

        n_start += BLOCK_N

    # Normalize
    out = acc / l_i[:, None]

    o_ptrs = O_ptr + z * stride_oz + h * stride_oh \
             + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = (offs_m[:, None] < M)
    tl.store(o_ptrs, out.to(tl.float16), mask=o_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    assert Q.dtype in (torch.float16, torch.bfloat16), "Q must be float16 or bfloat16"
    assert K.dtype == Q.dtype and V.dtype == Q.dtype, "K and V must match Q dtype"
    assert Q.device.type == K.device.type == V.device.type, "Q, K, V must be on the same device"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and Dq == Dqk and N == Nv, "Shape mismatch"
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Use CUDA tensors"
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    sm_scale = 1.0 / math.sqrt(Dq)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)

    _decoding_attn_fwd[grid](
        Q, K, V, O,
        Z, H, M, N,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
        D_HEAD_Q=Dq, D_HEAD_V=Dv,
    )
    return O
'''
        return {"code": code}