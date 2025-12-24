import textwrap

KERNEL_CODE = textwrap.dedent(r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 32}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64}, num_warps=8, num_stages=3),
    ],
    key=["M_CTX", "N_CTX"],
)
@triton.jit
def _gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qb: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kb: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vb: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_ob: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    sm_scale,
    M_CTX: tl.constexpr, N_CTX: tl.constexpr,
    D_HEAD: tl.constexpr, D_VALUE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    tl.multiple_of(stride_qm, 16)
    tl.multiple_of(stride_kn, 16)
    tl.multiple_of(stride_vn, 16)
    tl.multiple_of(stride_om, 16)

    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M_CTX

    offs_d = tl.arange(0, D_HEAD)
    q_ptrs = Q_ptr + pid_bh * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ_ptr + pid_bh * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd

    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)
    q = q * tl.sigmoid(gq)
    q = q * sm_scale
    q = q.to(tl.float16)

    offs_dv = tl.arange(0, D_VALUE)

    m_i = tl.where(mask_m, -float("inf"), 0.0).to(tl.float32)
    l_i = tl.where(mask_m, 0.0, 1.0).to(tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    log2e = 1.4426950408889634

    for start_n in tl.static_range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        k_ptrs = K_ptr + pid_bh * stride_kb + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        gk_ptrs = GK_ptr + pid_bh * stride_kb + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        k = k * tl.sigmoid(gk)
        k = k.to(tl.float16)

        v_ptrs = V_ptr + pid_bh * stride_vb + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)

        scores = tl.dot(q, tl.trans(k))
        mask_mn = mask_m[:, None] & mask_n[None, :]
        scores = tl.where(mask_mn, scores, -float("inf"))

        m_ij = tl.max(scores, axis=1)
        m_ij = tl.where(mask_m, m_ij, 0.0)
        m_new = tl.maximum(m_i, m_ij)

        alpha = tl.exp2((m_i - m_new) * log2e)
        p = tl.exp2((scores - m_new[:, None]) * log2e)
        p = tl.where(mask_mn, p, 0.0)
        l_new = l_i * alpha + tl.sum(p, axis=1)
        l_new = tl.where(mask_m, l_new, 1.0)

        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        m_i = m_new
        l_i = l_new

    out = acc / l_i[:, None]
    out = out.to(tl.float16)

    out_ptrs = O_ptr + pid_bh * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, out, mask=mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Zk == Z and Hk == H and Dk == Dq
    assert Zv == Z and Hv == H and Nv == N
    assert GQ.shape == Q.shape
    assert GK.shape == K.shape

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()
    if not GQ.is_contiguous():
        GQ = GQ.contiguous()
    if not GK.is_contiguous():
        GK = GK.contiguous()

    BH = Z * H
    Q3 = Q.reshape(BH, M, Dq)
    K3 = K.reshape(BH, N, Dq)
    V3 = V.reshape(BH, N, Dv)
    GQ3 = GQ.reshape(BH, M, Dq)
    GK3 = GK.reshape(BH, N, Dq)

    O3 = torch.empty((BH, M, Dv), device=Q.device, dtype=torch.float16)

    sm_scale = 1.0 / math.sqrt(Dq)

    grid = (triton.cdiv(M, 128), BH)

    _gdpa_fwd_kernel[grid](
        Q3, K3, V3, GQ3, GK3, O3,
        Q3.stride(0), Q3.stride(1), Q3.stride(2),
        K3.stride(0), K3.stride(1), K3.stride(2),
        V3.stride(0), V3.stride(1), V3.stride(2),
        O3.stride(0), O3.stride(1), O3.stride(2),
        sm_scale,
        M_CTX=M, N_CTX=N,
        D_HEAD=Dq, D_VALUE=Dv,
    )

    return O3.reshape(Z, H, M, Dv)
''')


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
