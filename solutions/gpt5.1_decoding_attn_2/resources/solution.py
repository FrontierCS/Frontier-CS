import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_N': 64, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64},
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64},
            num_warps=8,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 64, 'BLOCK_DMODEL': 128, 'BLOCK_DV': 64},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_N': 128, 'BLOCK_DMODEL': 128, 'BLOCK_DV': 64},
            num_warps=8,
            num_stages=3,
        ),
    ],
    key=['N'],
)
@triton.jit
def decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    Out_ptr,
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
    Z,
    H,
    M,
    N,
    Dv,
    sm_scale,
    D_HEAD: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    q_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_ptr = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_ptr = V_ptr + z_idx * stride_vz + h_idx * stride_vh
    o_ptr = Out_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om

    offs_v = tl.arange(0, BLOCK_DV)
    acc = tl.zeros((BLOCK_DV,), dtype=tl.float32)
    m_i = -float('inf')
    l_i = 0.0

    n_range = tl.arange(0, BLOCK_N)

    start_n = 0
    while start_n < N:
        offs_n = start_n + n_range
        n_mask = offs_n < N

        scores = tl.zeros((BLOCK_N,), dtype=tl.float32)

        d_start = 0
        while d_start < D_HEAD:
            offs_d = d_start + tl.arange(0, BLOCK_DMODEL)
            d_mask = offs_d < D_HEAD

            q_vals = tl.load(
                q_ptr + offs_d * stride_qd,
                mask=d_mask,
                other=0.0,
            )
            q_vals = q_vals.to(tl.float32)

            k_ptrs = (
                k_ptr
                + offs_n[:, None] * stride_kn
                + offs_d[None, :] * stride_kd
            )
            k_vals = tl.load(
                k_ptrs,
                mask=n_mask[:, None] & d_mask[None, :],
                other=0.0,
            )
            k_vals = k_vals.to(tl.float32)

            scores += tl.sum(k_vals * q_vals[None, :], axis=1)

            d_start += BLOCK_DMODEL

        scores = scores * sm_scale
        scores = tl.where(n_mask, scores, -float('inf'))

        max_score = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, max_score)

        alpha = tl.exp(m_i - m_new)
        l_i = l_i * alpha
        acc = acc * alpha

        p = tl.exp(scores - m_new)
        p = p * n_mask
        l_i = l_i + tl.sum(p, axis=0)

        v_ptrs = (
            v_ptr
            + offs_n[:, None] * stride_vn
            + offs_v[None, :] * stride_vd
        )
        v_mask = n_mask[:, None] & (offs_v[None, :] < Dv)
        v_vals = tl.load(
            v_ptrs,
            mask=v_mask,
            other=0.0,
        )
        v_vals = v_vals.to(tl.float32)

        acc += tl.sum(p[:, None] * v_vals, axis=0)

        m_i = m_new
        start_n += BLOCK_N

    acc = acc / l_i
    o_ptrs = o_ptr + offs_v * stride_od
    o_mask = offs_v < Dv
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16

    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4
    Zq, Hq, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Zq == Zk == Zv
    assert Hq == Hk == Hv
    assert Dq == Dk
    assert N == Nv

    Z = Zq
    H = Hq

    # Ensure contiguous for better memory access patterns
    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()

    sm_scale = 1.0 / math.sqrt(Dq)

    # Fallback to PyTorch if head dimensions are large (rare for decoding)
    MAX_D_HEAD_TRITON = 256
    MAX_DV_TRITON = 128
    if Dq > MAX_D_HEAD_TRITON or Dv > MAX_DV_TRITON:
        qf = Qc.to(torch.float32)
        kf = Kc.to(torch.float32)
        vf = Vc.to(torch.float32)
        attn_scores = torch.matmul(qf, kf.transpose(-1, -2)) * sm_scale
        attn_probs = torch.softmax(attn_scores, dim=-1)
        out = torch.matmul(attn_probs, vf)
        return out.to(torch.float16)

    Out = torch.empty((Z, H, M, Dv), device=Qc.device, dtype=torch.float16)

    grid = lambda meta: (Z * H * M,)

    decoding_attn_kernel[grid](
        Qc,
        Kc,
        Vc,
        Out,
        Qc.stride(0),
        Qc.stride(1),
        Qc.stride(2),
        Qc.stride(3),
        Kc.stride(0),
        Kc.stride(1),
        Kc.stride(2),
        Kc.stride(3),
        Vc.stride(0),
        Vc.stride(1),
        Vc.stride(2),
        Vc.stride(3),
        Out.stride(0),
        Out.stride(1),
        Out.stride(2),
        Out.stride(3),
        Z,
        H,
        M,
        N,
        Dv,
        sm_scale,
        D_HEAD=Dq,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
