import torch
import triton
import triton.language as tl
import inspect


@triton.jit
def _flash_attn_fwd(
    Q, K, V, Out,
    sm_scale,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_ob, stride_om, stride_od,
    B, M, N, D_HEAD, D_VALUE,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_d = offs_d < D_HEAD
    mask_dv = offs_dv < D_VALUE

    q_ptrs = Q + pid_bh * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    q = q.to(tl.float32)

    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.where(mask_m, m_i, 0.0)
    l_i = tl.where(mask_m, l_i, 1.0)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    k_ptrs_base = K + pid_bh * stride_kb
    v_ptrs_base = V + pid_bh * stride_vb

    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = k_ptrs_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        k = k.to(tl.float32)

        qk = tl.dot(q, tl.trans(k))
        qk = qk * sm_scale

        mask = mask_m[:, None] & mask_n[None, :]
        if CAUSAL:
            mask = mask & (offs_m[:, None] >= offs_n[None, :])

        qk = tl.where(mask, qk, -float('inf'))

        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)

        p = tl.exp(qk - m_new[:, None])
        l_ij = tl.sum(p, axis=1)

        l_new = l_i * tl.exp(m_i - m_new) + l_ij

        v_ptrs = v_ptrs_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)
        v = v.to(tl.float32)

        inv_l_new = 1.0 / l_new
        inv_l_new = tl.where(l_new > 0, inv_l_new, 0.0)
        scale_old = l_i * tl.exp(m_i - m_new) * inv_l_new
        scale_new = inv_l_new

        acc = acc * scale_old[:, None] + tl.dot(p, v) * scale_new[:, None]

        m_i = m_new
        l_i = l_new

        start_n += BLOCK_N

    out_ptrs = Out + pid_bh * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16

    Zq, Hq, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Zq == Zk == Zv
    assert Hq == Hk == Hv
    assert N == Nv
    assert Dq == Dk
    assert M <= 65535 and N <= 65535  # basic bounds for safety

    Z = Zq
    H = Hq
    B = Z * H

    Q_ = Q.contiguous().view(B, M, Dq)
    K_ = K.contiguous().view(B, N, Dk)
    V_ = V.contiguous().view(B, N, Dv)

    Out = torch.empty((B, M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    assert Dq <= BLOCK_DMODEL
    assert Dv <= BLOCK_DV

    stride_qb, stride_qm, stride_qd = Q_.stride()
    stride_kb, stride_kn, stride_kd = K_.stride()
    stride_vb, stride_vn, stride_vd = V_.stride()
    stride_ob, stride_om, stride_od = Out.stride()

    grid = (B, triton.cdiv(M, BLOCK_M))

    sm_scale = 1.0 / (float(Dq) ** 0.5)

    _flash_attn_fwd[grid](
        Q_, K_, V_, Out,
        sm_scale,
        stride_qb, stride_qm, stride_qd,
        stride_kb, stride_kn, stride_kd,
        stride_vb, stride_vn, stride_vd,
        stride_ob, stride_om, stride_od,
        B, M, N, Dq, Dv,
        CAUSAL=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return Out.view(Z, H, M, Dv)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_src = inspect.getsource(_flash_attn_fwd)
        func_src = inspect.getsource(flash_attn)
        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            + kernel_src
            + "\n\n"
            + func_src
            + "\n"
        )
        return {"code": code}