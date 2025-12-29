import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    batch_id = pid_zh // H
    head_id = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_dq = tl.arange(0, BLOCK_Dq)
    mask_dq = offs_dq < Dq

    offs_dv = tl.arange(0, BLOCK_Dv)
    mask_dv = offs_dv < Dv

    q_ptrs = (
        Q_ptr
        + batch_id * stride_qz
        + head_id * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_dq[None, :] * stride_qd
    )
    gq_ptrs = (
        GQ_ptr
        + batch_id * stride_gqz
        + head_id * stride_gqh
        + offs_m[:, None] * stride_gqm
        + offs_dq[None, :] * stride_gqd
    )

    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

    gate_q = 1.0 / (1.0 + tl.exp(-gq))
    q = q * gate_q

    m_i = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)

    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = (
            K_ptr
            + batch_id * stride_kz
            + head_id * stride_kh
            + offs_n[:, None] * stride_kn
            + offs_dq[None, :] * stride_kd
        )
        gk_ptrs = (
            GK_ptr
            + batch_id * stride_gkz
            + head_id * stride_gkh
            + offs_n[:, None] * stride_gkn
            + offs_dq[None, :] * stride_gkd
        )

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

        gate_k = 1.0 / (1.0 + tl.exp(-gk))
        k = k * gate_k

        qk = tl.dot(q, tl.trans(k)) * scale
        qk = tl.where(mask_n[None, :], qk, float("-inf"))

        block_max = tl.max(qk, axis=1)
        new_m_i = tl.maximum(m_i, block_max)
        p = tl.exp(qk - new_m_i[:, None])
        alpha = tl.exp(m_i - new_m_i)
        l_i = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = (
            V_ptr
            + batch_id * stride_vz
            + head_id * stride_vh
            + offs_n[:, None] * stride_vn
            + offs_dv[None, :] * stride_vd
        )
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        acc = acc * alpha[:, None] + tl.dot(p, v)
        m_i = new_m_i
        start_n += BLOCK_N

    acc = acc / l_i[:, None]

    o_ptrs = (
        O_ptr
        + batch_id * stride_oz
        + head_id * stride_oh
        + offs_m[:, None] * stride_om
        + offs_dv[None, :] * stride_od
    )
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda):
        raise ValueError("All tensors must be on CUDA device")
    if not (Q.dtype == K.dtype == V.dtype == GQ.dtype == GK.dtype == torch.float16):
        raise ValueError("All tensors must be float16")

    if Q.dim() != 4 or K.dim() != 4 or V.dim() != 4 or GQ.dim() != 4 or GK.dim() != 4:
        raise ValueError("All tensors must have 4 dimensions (Z, H, M/N, D)")

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dq_k = K.shape
    Zv, Hv, Nv, Dv = V.shape
    Zgq, Hgq, Mgq, Dq_gq = GQ.shape
    Zgk, Hgk, Ngk, Dq_gk = GK.shape

    if not (Z == Zk == Zv == Zgq == Zgk):
        raise ValueError("Batch dimension Z must match across all tensors")
    if not (H == Hk == Hv == Hgq == Hgk):
        raise ValueError("Head dimension H must match across all tensors")
    if not (M == Mgq and N == Nv == Ngk and Dq == Dq_k == Dq_gq == Dq_gk):
        raise ValueError("Incompatible tensor shapes")
    if M != N:
        raise ValueError("For GDPA, query and key sequence lengths must be equal (M == N)")

    device = Q.device
    O = torch.empty((Z, H, M, Dv), device=device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    def _next_power_of_2(x: int) -> int:
        return 1 << (x - 1).bit_length()

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_Dq = _next_power_of_2(Dq)
    BLOCK_Dv = _next_power_of_2(Dv)

    def _ceil_div(a: int, b: int) -> int:
        return (a + b - 1) // b

    grid = (Z * H, _ceil_div(M, BLOCK_M))
    scale = 1.0 / math.sqrt(Dq)

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv,
        num_warps=4,
        num_stages=2,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}