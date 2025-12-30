import textwrap

KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634

@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qb: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kb: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vb: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_ob: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    sm_scale,
    M: tl.constexpr, N: tl.constexpr, D_HEAD: tl.constexpr, D_V: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    CAUSAL: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n0 = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_V)

    q_ptrs = Q_ptr + pid_b * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q_mask = offs_m[:, None] < M
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float16)

    m_i = tl.full([BLOCK_M], -float("inf"), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, D_V], tl.float32)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + offs_n0
        n_mask = offs_n < N

        k_ptrs = K_ptr + pid_b * stride_kb + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        v_ptrs = V_ptr + pid_b * stride_vb + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

        qk = tl.dot(q, tl.trans(k)).to(tl.float32) * sm_scale

        qk = tl.where(n_mask[None, :], qk, -float("inf"))
        if CAUSAL:
            qk = tl.where(offs_n[None, :] <= offs_m[:, None], qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        alpha = tl.exp2((m_i - m_ij) * _LOG2E)
        p = tl.exp2((qk - m_ij[:, None]) * _LOG2E)

        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)

        m_i = m_ij

    row_mask = offs_m < M
    l_safe = tl.where(row_mask, l_i, 1.0)
    out = (acc / l_safe[:, None]).to(tl.float16)

    o_ptrs = O_ptr + pid_b * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = row_mask[:, None]
    tl.store(o_ptrs, out, mask=o_mask)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Zk == Z and Hk == H and Zv == Z and Hv == H
    assert N == Nv
    assert Dk == Dq

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()

    BH = Z * H
    Q3 = Q.reshape(BH, M, Dq)
    K3 = K.reshape(BH, N, Dq)
    V3 = V.reshape(BH, N, Dv)

    O3 = torch.empty((BH, M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 128
    BLOCK_N = 64

    grid = (triton.cdiv(M, BLOCK_M), BH)

    sm_scale = 1.0 / math.sqrt(Dq)

    _flash_attn_fwd[grid](
        Q3, K3, V3, O3,
        Q3.stride(0), Q3.stride(1), Q3.stride(2),
        K3.stride(0), K3.stride(1), K3.stride(2),
        V3.stride(0), V3.stride(1), V3.stride(2),
        O3.stride(0), O3.stride(1), O3.stride(2),
        sm_scale,
        M=M, N=N, D_HEAD=Dq, D_V=Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        CAUSAL=causal,
        num_warps=4,
        num_stages=3,
    )

    return O3.reshape(Z, H, M, Dv)
'''

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": textwrap.dedent(KERNEL_CODE).lstrip()}