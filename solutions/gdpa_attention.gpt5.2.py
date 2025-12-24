import textwrap

KERNEL_CODE = textwrap.dedent(r"""
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    DQ: tl.constexpr, DV: tl.constexpr,
    M_CTX: tl.constexpr, N_CTX: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_z = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, DQ)
    offs_dv = tl.arange(0, DV)

    q_base = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
    k_base = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    v_base = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    gq_base = GQ_ptr + pid_z * stride_qz + pid_h * stride_qh
    gk_base = GK_ptr + pid_z * stride_kz + pid_h * stride_kh
    o_base = O_ptr + pid_z * stride_oz + pid_h * stride_oh

    mask_m = offs_m < M_CTX

    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = gq_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float16)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float16)
    q = q * tl.sigmoid(gq)

    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, DV), tl.float32)

    sm_scale = 1.0 / math.sqrt(float(DQ))

    for start_n in tl.static_range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        gk_ptrs = gk_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)
        k = k * tl.sigmoid(gk)

        scores = tl.dot(q, tl.trans(k)).to(tl.float32) * sm_scale
        scores = tl.where(mask_m[:, None] & mask_n[None, :], scores, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_ij)

        p = tl.exp(scores - m_ij[:, None])
        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None]

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)
        acc += tl.dot(tl.cast(p, tl.float16), v).to(tl.float32)

        m_i = m_ij

    inv_l = 1.0 / l_i
    acc = acc * inv_l[:, None]
    acc = tl.where(mask_m[:, None], acc, 0.0)

    o_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, tl.cast(acc, tl.float16), mask=mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16 or GQ.dtype != torch.float16 or GK.dtype != torch.float16:
        raise ValueError("All inputs must be torch.float16.")
    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4 or GQ.ndim != 4 or GK.ndim != 4:
        raise ValueError("All inputs must be 4D: (Z, H, M/N, D).")

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    if Zk != Z or Hk != H or Zv != Z or Hv != H:
        raise ValueError("Batch/head dimensions must match across Q/K/V.")
    if Nv != N:
        raise ValueError("V sequence length must match K sequence length.")
    if DQk != DQ:
        raise ValueError("Q and K last dim must match.")
    if GQ.shape != Q.shape:
        raise ValueError("GQ must have same shape as Q.")
    if GK.shape != K.shape:
        raise ValueError("GK must have same shape as K.")

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    # Heuristic config
    if DQ == 64 and DV == 64:
        if M >= 1024:
            BLOCK_M = 128
            BLOCK_N = 64
            num_warps = 8
            num_stages = 4
        else:
            BLOCK_M = 64
            BLOCK_N = 64
            num_warps = 4
            num_stages = 4
    else:
        # generic, conservative
        BLOCK_M = 64
        BLOCK_N = 64
        num_warps = 4
        num_stages = 3

    grid = (triton.cdiv(M, BLOCK_M), H, Z)

    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        DQ=DQ, DV=DV,
        M_CTX=M, N_CTX=N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
""")


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
