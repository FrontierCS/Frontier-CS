import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
    ],
    key=['M_CTX', 'N_CTX', 'CAUSAL'],
)
@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    Z: tl.constexpr, H: tl.constexpr,
    M_CTX: tl.constexpr, N_CTX: tl.constexpr,
    D_HEAD: tl.constexpr, D_V: tl.constexpr,
    SM_SCALE: tl.constexpr,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    num_m_blocks = tl.cdiv(M_CTX, BLOCK_M)
    bh = pid // num_m_blocks
    pid_m = pid - bh * num_m_blocks
    z = bh // H
    h = bh - z * H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)

    q_base = Q_ptr + z * stride_qz + h * stride_qh
    k_base = K_ptr + z * stride_kz + h * stride_kh
    v_base = V_ptr + z * stride_vz + h * stride_vh
    o_base = O_ptr + z * stride_oz + h * stride_oh

    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q_mask = offs_m < M_CTX
    q = tl.load(q_ptrs, mask=q_mask[:, None], other=0.0).to(tl.float16)

    m_i = tl.full([BLOCK_M], -float("inf"), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, D_V], tl.float32)

    # hints (best-effort)
    tl.multiple_of(stride_qm, 16)
    tl.multiple_of(stride_kn, 16)
    tl.multiple_of(stride_vn, 16)
    tl.multiple_of(stride_om, 16)

    offs_dv = tl.arange(0, D_V)

    for start_n in tl.static_range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N_CTX

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

        qk = tl.dot(q, tl.trans(k))
        qk = qk.to(tl.float32) * SM_SCALE

        if CAUSAL:
            causal_mask = offs_n[None, :] <= offs_m[:, None]
            qk = tl.where(causal_mask, qk, -float("inf"))

        qk = tl.where(n_mask[None, :], qk, -float("inf"))

        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)

        exp_m = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])

        l_new = l_i * exp_m + tl.sum(p, axis=1)

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

        acc = acc * exp_m[:, None] + tl.dot(p.to(tl.float16), v)

        m_i = m_new
        l_i = l_new

    inv_l = 1.0 / l_i
    out = acc * inv_l[:, None]
    out = out.to(tl.float16)

    o_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=q_mask[:, None])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, D = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and D == Dk and N == Nv

    # optimized path for typical dims; otherwise fallback
    if D % 16 != 0 or Dv % 16 != 0:
        q = Q.to(torch.float32)
        k = K.to(torch.float32)
        v = V.to(torch.float32)
        scale = 1.0 / math.sqrt(D)
        attn = torch.matmul(q, k.transpose(-1, -2)) * scale
        if causal:
            i = torch.arange(M, device=Q.device)
            j = torch.arange(N, device=Q.device)
            mask = j[None, :] <= i[:, None]
            attn = attn.masked_fill(~mask, float('-inf'))
        p = torch.softmax(attn, dim=-1)
        out = torch.matmul(p, v).to(torch.float16)
        return out

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    grid = lambda meta: (Z * H * triton.cdiv(M, meta['BLOCK_M']),)

    _flash_attn_fwd[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z=Z, H=H,
        M_CTX=M, N_CTX=N,
        D_HEAD=D, D_V=Dv,
        SM_SCALE=(1.0 / math.sqrt(D)),
        CAUSAL=causal,
    )
    return O
'''
        return {"code": textwrap.dedent(code)}