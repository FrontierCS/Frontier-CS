import math
import os
import torch
import triton
import triton.language as tl

KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    sm_scale,
    Z: tl.constexpr, H: tl.constexpr, M: tl.constexpr,
    N_CTX: tl.constexpr, DQ: tl.constexpr, DV: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)

    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    q_base = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    d_offsets = tl.arange(0, DQ)
    tl.multiple_of(DQ, 8)
    q = tl.load(q_base + d_offsets * stride_qd).to(tl.float32)

    m_i = tl.full((), -1.0e20, tl.float32)
    l_i = tl.zeros((), tl.float32)
    dv_offsets = tl.arange(0, DV)
    tl.multiple_of(DV, 8)
    acc = tl.zeros([DV], tl.float32)

    k_base = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_base = V_ptr + z_idx * stride_vz + h_idx * stride_vh

    for start_n in range(0, N_CTX, BLOCK_N):
        n_offsets = start_n + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N_CTX

        k = tl.load(
            k_base + n_offsets[:, None] * stride_kn + d_offsets[None, :] * stride_kd,
            mask=n_mask[:, None],
            other=0.0,
        ).to(tl.float32)

        qk = tl.sum(k * q[None, :], axis=1) * sm_scale
        qk = tl.where(n_mask, qk, -1.0e20)

        m_block = tl.max(qk, axis=0)
        m_new = tl.maximum(m_i, m_block)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new)

        l_new = l_i * alpha + tl.sum(p, axis=0)

        v = tl.load(
            v_base + n_offsets[:, None] * stride_vn + dv_offsets[None, :] * stride_vd,
            mask=n_mask[:, None],
            other=0.0,
        ).to(tl.float32)

        acc = acc * alpha + tl.sum(v * p[:, None], axis=0)

        m_i = m_new
        l_i = l_new

    out = acc / l_i
    o_base = O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om
    tl.store(o_base + dv_offsets * stride_od, out.to(tl.float16))


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Zv == Z
    assert Hk == H and Hv == H
    assert Nv == N
    assert DQk == DQ
    assert DV == V.shape[-1]

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    sm_scale = 1.0 / math.sqrt(DQ)

    if N >= 4096:
        BLOCK_N = 512
        num_warps = 8
        num_stages = 4
    elif N >= 2048:
        BLOCK_N = 256
        num_warps = 8
        num_stages = 4
    else:
        BLOCK_N = 256
        num_warps = 4
        num_stages = 3

    grid = (Z * H * M,)

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
        Z=Z, H=H, M=M,
        N_CTX=N, DQ=DQ, DV=DV,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
'''

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
