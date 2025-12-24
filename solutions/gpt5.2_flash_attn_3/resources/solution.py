import textwrap

_KERNEL_CODE = textwrap.dedent(r"""
import math
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634


@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_ob, stride_om, stride_od,
    M: tl.constexpr, N: tl.constexpr,
    D_HEAD: tl.constexpr, D_V: tl.constexpr,
    SM_SCALE_LOG2E: tl.constexpr,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, D_HEAD)
    tl.multiple_of(offs_d, 16)
    tl.max_contiguous(offs_d, 16)

    q_ptrs = Q_ptr + pid_b * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float16)

    offs_dv = tl.arange(0, D_V)
    tl.multiple_of(offs_dv, 16)
    tl.max_contiguous(offs_dv, 16)

    m_i = tl.where(mask_m, -float("inf"), 0.0).to(tl.float32)
    l_i = tl.where(mask_m, 0.0, 1.0).to(tl.float32)
    acc = tl.zeros([BLOCK_M, D_V], dtype=tl.float32)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = K_ptr + pid_b * stride_kb + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0).to(tl.float16)

        v_ptrs = V_ptr + pid_b * stride_vb + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)

        qk = tl.dot(q, k).to(tl.float32)
        qk = qk * SM_SCALE_LOG2E

        attn_mask = mask_m[:, None] & mask_n[None, :]
        if CAUSAL:
            attn_mask = attn_mask & (offs_m[:, None] >= offs_n[None, :])

        qk = tl.where(attn_mask, qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        p = tl.exp2(qk - m_ij[:, None])

        alpha = tl.exp2(m_i - m_ij)
        l_ij = l_i * alpha + tl.sum(p, axis=1)

        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)

        m_i = m_ij
        l_i = l_ij

    o = acc / l_i[:, None]
    o_ptrs = O_ptr + pid_b * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, D_HEAD = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, D_V = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and D_HEAD == Dk
    assert K.shape[2] == V.shape[2]

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()

    B = Z * H
    Q3 = Q.view(B, M, D_HEAD)
    K3 = K.view(B, N, D_HEAD)
    V3 = V.view(B, N, D_V)

    O = torch.empty((B, M, D_V), device=Q.device, dtype=torch.float16)

    if M <= 1024:
        BLOCK_M = 64
        BLOCK_N = 128
        num_warps = 4
        num_stages = 4
    else:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 8
        num_stages = 3

    sm_scale_log2e = (1.0 / math.sqrt(D_HEAD)) * _LOG2E

    grid = (triton.cdiv(M, BLOCK_M), B)
    _flash_attn_fwd[grid](
        Q3, K3, V3, O,
        Q3.stride(0), Q3.stride(1), Q3.stride(2),
        K3.stride(0), K3.stride(1), K3.stride(2),
        V3.stride(0), V3.stride(1), V3.stride(2),
        O.stride(0), O.stride(1), O.stride(2),
        M=M, N=N,
        D_HEAD=D_HEAD, D_V=D_V,
        SM_SCALE_LOG2E=sm_scale_log2e,
        CAUSAL=causal,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return O.view(Z, H, M, D_V)
""").strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
