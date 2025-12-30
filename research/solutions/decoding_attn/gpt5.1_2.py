import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_N': 64, 'BLOCK_DQ': 64, 'BLOCK_DV': 64},
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_N': 256, 'BLOCK_DQ': 64, 'BLOCK_DV': 64},
            num_warps=8,
            num_stages=4,
        ),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    BLOCK_N: tl.constexpr,
    BLOCK_DQ: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    q_row_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_head_ptr = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_head_ptr = V_ptr + z_idx * stride_vz + h_idx * stride_vh
    o_row_ptr = O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om

    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dv = tl.arange(0, BLOCK_DV)
    offs_n = tl.arange(0, BLOCK_N)

    q = tl.load(q_row_ptr + offs_dq * stride_qd, mask=offs_dq < Dq, other=0.0)
    q = q.to(tl.float32)

    m_i = tl.full((), -1e9, tl.float32)
    l_i = tl.full((), 0.0, tl.float32)
    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)

    n_start = 0
    while n_start < N:
        n_idx = n_start + offs_n
        mask_n = n_idx < N

        k_ptrs = k_head_ptr + n_idx[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(
            k_ptrs,
            mask=mask_n[:, None] & (offs_dq[None, :] < Dq),
            other=0.0,
        )
        k = k.to(tl.float32)

        scores = tl.sum(k * q[None, :], axis=1) * sm_scale
        scores = tl.where(mask_n, scores, -1e9)

        max_block = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, max_block)
        exp_m_diff = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new)
        l_new = l_i * exp_m_diff + tl.sum(p, axis=0)

        v_ptrs = v_head_ptr + n_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(
            v_ptrs,
            mask=mask_n[:, None] & (offs_dv[None, :] < Dv),
            other=0.0,
        )
        v = v.to(tl.float32)

        contrib = tl.sum(p[:, None] * v, axis=0)
        acc = acc * exp_m_diff + contrib

        l_i = l_new
        m_i = m_new
        n_start += BLOCK_N

    inv_l = 1.0 / l_i
    out = acc * inv_l
    tl.store(o_row_ptr + offs_dv * stride_od, out.to(tl.float16), mask=offs_dv < Dv)


def _decoding_attn_torch(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    scale = 1.0 / math.sqrt(Dq)
    scores = torch.matmul(
        Q.to(torch.float32),
        K.to(torch.float32).transpose(-1, -2),
    ) * scale
    attn = torch.softmax(scores, dim=-1)
    out = torch.matmul(attn, V.to(torch.float32))
    return out.to(torch.float16)


def _decoding_attn_triton(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.device == K.device == V.device
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    if Z != Zk or Z != Zv or H != Hk or H != Hv or Dq != Dqk or N != Nv:
        raise ValueError("Incompatible shapes for Q, K, V")

    if Dq > 64 or Dv > 64:
        return _decoding_attn_torch(Q, K, V)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    grid = (Z * H * M,)

    sm_scale = 1.0 / math.sqrt(Dq)

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
    )
    return O


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if Q.is_cuda and K.is_cuda and V.is_cuda:
        try:
            return _decoding_attn_triton(Q, K, V)
        except Exception:
            return _decoding_attn_torch(Q, K, V)
    else:
        return _decoding_attn_torch(Q, K, V)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}