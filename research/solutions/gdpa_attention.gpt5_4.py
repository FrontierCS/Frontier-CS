import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale: tl.float32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, Dq)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dq = offs_dq < Dq
    mask_dv = offs_dv < Dv

    base_q = z * stride_qz + h * stride_qh
    base_k = z * stride_kz + h * stride_kh
    base_v = z * stride_vz + h * stride_vh
    base_gq = z * stride_gqz + h * stride_gqh
    base_gk = z * stride_gkz + h * stride_gkh
    base_o = z * stride_oz + h * stride_oh

    q_ptrs = Q_ptr + base_q + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = GQ_ptr + base_gq + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd
    q_mask = mask_m[:, None] & mask_dq[None, :]

    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    # sigmoid gating
    gq = 1.0 / (1.0 + tl.exp(-gq))
    qg = q * gq

    m_i = tl.full([BLOCK_M], -1.0e9, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    n_tiles = tl.cdiv(N, BLOCK_N)
    for t in range(0, n_tiles):
        start_n = t * BLOCK_N
        n_idx = start_n + offs_n
        mask_n = n_idx < N

        k_ptrs = K_ptr + base_k + n_idx[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        gk_ptrs = GK_ptr + base_gk + n_idx[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gk = 1.0 / (1.0 + tl.exp(-gk))
        kg = k * gk

        qk = tl.dot(qg, tl.trans(kg)) * sm_scale
        # mask out invalid rows/cols
        qk = tl.where(mask_m[:, None] & mask_n[None, :], qk, -1.0e9)

        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_new[:, None])
        alpha = tl.exp(m_i - m_new)
        l_i = l_i * alpha + tl.sum(p, 1)

        v_ptrs = V_ptr + base_v + n_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        acc = acc * alpha[:, None] + tl.dot(p, v)
        m_i = m_new

    acc = acc / l_i[:, None]
    o_ptrs = O_ptr + base_o + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = mask_m[:, None] & mask_dv[None, :]
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16, "All tensors must be float16"
    assert Q.shape[:3] == GQ.shape[:3] and Q.shape[3] == GQ.shape[3], "GQ shape mismatch"
    assert K.shape[:3] == GK.shape[:3] and K.shape[3] == GK.shape[3], "GK shape mismatch"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and Dq == Dqk, "Shape mismatch across Q/K/V"
    device = Q.device

    O = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=device)

    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    sm_scale = 1.0 / math.sqrt(Dq)

    # Tiling parameters
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DV = 128 if Dv > 64 else 64

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    num_warps = 4 if (Dq <= 64 and Dv <= 64) else 8
    num_stages = 2

    gdpa_kernel[grid](
        Q, K, V, GQ, GK, O,
        Z, H, M, N, Dq, Dv,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps, num_stages=num_stages,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale: tl.float32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, Dq)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dq = offs_dq < Dq
    mask_dv = offs_dv < Dv

    base_q = z * stride_qz + h * stride_qh
    base_k = z * stride_kz + h * stride_kh
    base_v = z * stride_vz + h * stride_vh
    base_gq = z * stride_gqz + h * stride_gqh
    base_gk = z * stride_gkz + h * stride_gkh
    base_o = z * stride_oz + h * stride_oh

    q_ptrs = Q_ptr + base_q + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = GQ_ptr + base_gq + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd
    q_mask = mask_m[:, None] & mask_dq[None, :]

    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    gq = 1.0 / (1.0 + tl.exp(-gq))
    qg = q * gq

    m_i = tl.full([BLOCK_M], -1.0e9, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    n_tiles = tl.cdiv(N, BLOCK_N)
    for t in range(0, n_tiles):
        start_n = t * BLOCK_N
        n_idx = start_n + offs_n
        mask_n = n_idx < N

        k_ptrs = K_ptr + base_k + n_idx[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        gk_ptrs = GK_ptr + base_gk + n_idx[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)
        gk = 1.0 / (1.0 + tl.exp(-gk))
        kg = k * gk

        qk = tl.dot(qg, tl.trans(kg)) * sm_scale
        qk = tl.where(mask_m[:, None] & mask_n[None, :], qk, -1.0e9)

        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_new[:, None])
        alpha = tl.exp(m_i - m_new)
        l_i = l_i * alpha + tl.sum(p, 1)

        v_ptrs = V_ptr + base_v + n_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        acc = acc * alpha[:, None] + tl.dot(p, v)
        m_i = m_new

    acc = acc / l_i[:, None]
    o_ptrs = O_ptr + base_o + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = mask_m[:, None] & mask_dv[None, :]
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16, "All tensors must be float16"
    assert Q.shape[:3] == GQ.shape[:3] and Q.shape[3] == GQ.shape[3], "GQ shape mismatch"
    assert K.shape[:3] == GK.shape[:3] and K.shape[3] == GK.shape[3], "GK shape mismatch"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and Dq == Dqk, "Shape mismatch across Q/K/V"
    device = Q.device

    O = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=device)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    sm_scale = 1.0 / math.sqrt(Dq)

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DV = 128 if Dv > 64 else 64

    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    num_warps = 4 if (Dq <= 64 and Dv <= 64) else 8
    num_stages = 2

    gdpa_kernel[grid](
        Q, K, V, GQ, GK, O,
        Z, H, M, N, Dq, Dv,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps, num_stages=num_stages,
    )
    return O
'''
        return {"code": code}
