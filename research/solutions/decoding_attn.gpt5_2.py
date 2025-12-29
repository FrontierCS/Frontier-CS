import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 256, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 256, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    softmax_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(0)
    M_BLOCKS = tl.cdiv(M, BLOCK_M)
    qh_id = pid // M_BLOCKS
    m_block_id = pid % M_BLOCKS

    h_id = qh_id % H
    z_id = qh_id // H

    m_start = m_block_id * BLOCK_M

    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dq = offs_dq < Dq
    mask_dv = offs_dv < Dv

    q_ptrs = Q_ptr + z_id * stride_qz + h_id * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

    m_i = tl.full([BLOCK_M], -float('inf'), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], tl.float32)

    n_iter = tl.cdiv(N, BLOCK_N)
    for n_idx in range(0, n_iter):
        n_start = n_idx * BLOCK_N
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = K_ptr + z_id * stride_kz + h_id * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = V_ptr + z_id * stride_vz + h_id * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k))
        qk = qk * softmax_scale
        qk = tl.where(mask_n[None, :], qk, -float('inf'))

        row_max = tl.max(qk, 1)
        m_new = tl.maximum(m_i, row_max)

        m_i_safe = tl.where(mask_m, m_i, 0.0)
        m_new_safe = tl.where(mask_m, m_new, 0.0)

        p = tl.exp(qk - m_new_safe[:, None])

        l_i = tl.where(mask_m, tl.exp(m_i_safe - m_new_safe) * l_i + tl.sum(p, 1), l_i)

        acc = acc * tl.exp(m_i_safe - m_new_safe)[:, None]
        acc += tl.dot(p.to(tl.float32), v)

        m_i = m_new

    denom = tl.where(mask_m, l_i, 1.0)
    out = acc / denom[:, None]

    o_ptrs = O_ptr + z_id * stride_oz + h_id * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Input dtypes must be float16"
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Q, K, V must be 4D tensors (Z, H, M/N, D)"
    Zq, Hq, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Zq == Zk == Zv, "Batch Z must match"
    assert Hq == Hk == Hv, "Heads H must match"
    assert Dq == Dk, "Q and K last dims must match"
    assert N == Nv, "K and V sequence length must match"
    Z, H = Zq, Hq

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    softmax_scale = 1.0 / math.sqrt(float(Dq))

    grid = lambda META: (int(Z * H * triton.cdiv(M, META['BLOCK_M'])),)

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        softmax_scale,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 256, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 256, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    softmax_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(0)
    M_BLOCKS = tl.cdiv(M, BLOCK_M)
    qh_id = pid // M_BLOCKS
    m_block_id = pid % M_BLOCKS

    h_id = qh_id % H
    z_id = qh_id // H

    m_start = m_block_id * BLOCK_M

    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dq = offs_dq < Dq
    mask_dv = offs_dv < Dv

    q_ptrs = Q_ptr + z_id * stride_qz + h_id * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

    m_i = tl.full([BLOCK_M], -float('inf'), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], tl.float32)

    n_iter = tl.cdiv(N, BLOCK_N)
    for n_idx in range(0, n_iter):
        n_start = n_idx * BLOCK_N
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = K_ptr + z_id * stride_kz + h_id * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = V_ptr + z_id * stride_vz + h_id * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k))
        qk = qk * softmax_scale
        qk = tl.where(mask_n[None, :], qk, -float('inf'))

        row_max = tl.max(qk, 1)
        m_new = tl.maximum(m_i, row_max)

        m_i_safe = tl.where(mask_m, m_i, 0.0)
        m_new_safe = tl.where(mask_m, m_new, 0.0)

        p = tl.exp(qk - m_new_safe[:, None])

        l_i = tl.where(mask_m, tl.exp(m_i_safe - m_new_safe) * l_i + tl.sum(p, 1), l_i)

        acc = acc * tl.exp(m_i_safe - m_new_safe)[:, None]
        acc += tl.dot(p.to(tl.float32), v)

        m_i = m_new

    denom = tl.where(mask_m, l_i, 1.0)
    out = acc / denom[:, None]

    o_ptrs = O_ptr + z_id * stride_oz + h_id * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Input dtypes must be float16"
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Q, K, V must be 4D tensors (Z, H, M/N, D)"
    Zq, Hq, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Zq == Zk == Zv, "Batch Z must match"
    assert Hq == Hk == Hv, "Heads H must match"
    assert Dq == Dk, "Q and K last dims must match"
    assert N == Nv, "K and V sequence length must match"
    Z, H = Zq, Hq

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    softmax_scale = 1.0 / math.sqrt(float(Dq))

    grid = lambda META: (int(Z * H * triton.cdiv(M, META['BLOCK_M'])),)

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        softmax_scale,
    )

    return O
'''
        return {"code": code}