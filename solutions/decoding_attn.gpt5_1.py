import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64, "BLOCK_DMODEL": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64}, num_warps=8, num_stages=3),
    ],
    key=["N"],
)
@triton.jit
def _decoding_attn_stats_kernel(
    Q_ptr, K_ptr, M_ptr, L_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_mz, stride_mh, stride_mm,
    stride_lz, stride_lh, stride_lm,
    Z, H, M, N, D, scale: tl.constexpr,
    BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    m_idx = pid % M
    pid = pid // M
    h_idx = pid % H
    z_idx = pid // H

    # Base pointers
    q_row_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_base_ptr = K_ptr + z_idx * stride_kz + h_idx * stride_kh

    running_m = tl.full([], -float("inf"), tl.float32)
    running_l = tl.zeros([], tl.float32)

    n0 = 0
    while n0 < N:
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        logits = tl.zeros([BLOCK_N], dtype=tl.float32)

        d0 = 0
        while d0 < D:
            offs_d = d0 + tl.arange(0, BLOCK_DMODEL)
            mask_d = offs_d < D

            q_sub = tl.load(q_row_ptr + offs_d * stride_qd, mask=mask_d, other=0).to(tl.float32)  # [BD]

            k_ptrs = k_base_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
            k_tile = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0).to(tl.float32)  # [BN, BD]

            logits += tl.sum(k_tile * q_sub[None, :], axis=1)

            d0 += BLOCK_DMODEL

        logits = logits * scale
        logits = tl.where(mask_n, logits, -float("inf"))

        m_curr = tl.max(logits, axis=0)
        m_new = tl.maximum(running_m, m_curr)
        alpha = tl.exp(running_m - m_new)
        p = tl.exp(logits - m_new)
        l_new = running_l * alpha + tl.sum(p, axis=0)

        running_m = m_new
        running_l = l_new

        n0 += BLOCK_N

    # Store results
    m_ptr = M_ptr + z_idx * stride_mz + h_idx * stride_mh + m_idx * stride_mm
    l_ptr = L_ptr + z_idx * stride_lz + h_idx * stride_lh + m_idx * stride_lm
    tl.store(m_ptr, running_m)
    tl.store(l_ptr, running_l)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DV": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DV": 128}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=8, num_stages=3),
    ],
    key=["N", "Dv"],
)
@triton.jit
def _decoding_attn_out_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, M_ptr, L_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, D, Dv, scale: tl.constexpr,
    BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    m_idx = pid % M
    pid = pid // M
    h_idx = pid % H
    z_idx = pid // H

    q_row_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_base_ptr = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_base_ptr = V_ptr + z_idx * stride_vz + h_idx * stride_vh
    o_row_ptr = O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om

    m_ptr = M_ptr + z_idx * stride_oz // stride_od * 0 + z_idx * 0  # dummy to get type
    m_ptr = M_ptr + z_idx * stride_oz * 0 + h_idx * 0 + m_idx * 0  # no-op, keep type
    m_row_ptr = M_ptr + z_idx * stride_qz * 0 + h_idx * 0 + m_idx * 0  # keep type

    # Load stats
    stat_m_ptr = M_ptr + z_idx * stride_qz * 0 + h_idx * 0 + m_idx * 0  # placeholder to keep type
    stat_m_ptr = M_ptr + z_idx * stride_qz * 0  # dummy
    m_val = tl.load(M_ptr + z_idx * 0 + h_idx * 0 + m_idx * 0)  # not used; replaced below

    # Correct stat pointers
    s_m_ptr = M_ptr + z_idx * stride_oz // stride_od * 0  # just to silence analysis
    s_m_ptr = M_ptr + z_idx * 0  # no-op
    m_stat_ptr = M_ptr + z_idx * 0 + h_idx * 0 + m_idx * 0  # no-op

    # Actually compute correct stat ptrs using provided strides
    m_stat_ptr = M_ptr + z_idx * stride_qz * 0  # not correct; reassign below to final
    # We'll recompute manually with given strides for stats: M: (Z,H,M)
    # We passed stride_mz, stride_mh, stride_mm as parts of args earlier; But this kernel signature does not include them.
    # To avoid confusion, we will compute stats location below via extra arguments.
    # However to keep kernel signature simpler, we will pass stats strides directly as extra arguments.

    # This kernel signature must include stats strides. We re-declare function with extra args.
    # This block is bypassed due to proper function arguments below.
    pass


# Redefine kernel with correct signature (the above definition is a placeholder to ensure proper compilation order)
@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DV": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DV": 128}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DV": 64}, num_warps=8, num_stages=3),
    ],
    key=["N", "Dv"],
)
@triton.jit
def _decoding_attn_out_kernel_v2(
    Q_ptr, K_ptr, V_ptr, O_ptr, M_stat_ptr, L_stat_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    stride_mz, stride_mh, stride_mm,
    stride_lz, stride_lh, stride_lm,
    Z, H, M, N, D, Dv, scale: tl.constexpr,
    BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    m_idx = pid % M
    pid = pid // M
    h_idx = pid % H
    z_idx = pid // H

    q_row_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_base_ptr = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_base_ptr = V_ptr + z_idx * stride_vz + h_idx * stride_vh
    o_row_ptr = O_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om

    # Load precomputed stats
    m_ptr = M_stat_ptr + z_idx * stride_mz + h_idx * stride_mh + m_idx * stride_mm
    l_ptr = L_stat_ptr + z_idx * stride_lz + h_idx * stride_lh + m_idx * stride_lm
    m_val = tl.load(m_ptr).to(tl.float32)
    l_val = tl.load(l_ptr).to(tl.float32)

    dv0 = 0
    while dv0 < Dv:
        offs_dv = dv0 + tl.arange(0, BLOCK_DV)
        mask_dv = offs_dv < Dv
        o_tile = tl.zeros([BLOCK_DV], dtype=tl.float32)

        n0 = 0
        while n0 < N:
            offs_n = n0 + tl.arange(0, BLOCK_N)
            mask_n = offs_n < N

            logits = tl.zeros([BLOCK_N], dtype=tl.float32)

            d0 = 0
            while d0 < D:
                offs_d = d0 + tl.arange(0, BLOCK_DMODEL)
                mask_d = offs_d < D

                q_sub = tl.load(q_row_ptr + offs_d * stride_qd, mask=mask_d, other=0).to(tl.float32)

                k_ptrs = k_base_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
                k_tile = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0).to(tl.float32)
                logits += tl.sum(k_tile * q_sub[None, :], axis=1)

                d0 += BLOCK_DMODEL

            logits = logits * scale
            logits = tl.where(mask_n, logits, -float("inf"))
            p = tl.exp(logits - m_val) / l_val  # [BN]

            v_ptrs = v_base_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v_tile = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0).to(tl.float32)  # [BN, BDV]

            o_tile += tl.sum(v_tile * p[:, None], axis=0)

            n0 += BLOCK_N

        tl.store(o_row_ptr + offs_dv * stride_od, o_tile.to(tl.float16), mask=mask_dv)

        dv0 += BLOCK_DV


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        # Fallback to PyTorch on CPU; on GPU, prefer Triton
        Dq = Q.shape[-1]
        scale = 1.0 / math.sqrt(Dq)
        # Q: (Z,H,M,Dq), K: (Z,H,N,Dq), V: (Z,H,N,Dv)
        logits = torch.einsum("zhmd,zhnd->zhmn", Q.float(), K.float()) * scale
        probs = torch.softmax(logits, dim=-1).to(V.dtype)
        out = torch.einsum("zhmn,zhnd->zhmd", probs, V)
        return out

    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype in (torch.float16, torch.bfloat16) and V.dtype in (torch.float16, torch.bfloat16)
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    _, _, N2, Dv = V.shape
    assert Dk == Dq and N2 == N

    device = Q.device
    scale = 1.0 / math.sqrt(Dq)

    # Allocate stats buffers
    M_stat = torch.empty((Z, H, M), dtype=torch.float32, device=device)
    L_stat = torch.empty((Z, H, M), dtype=torch.float32, device=device)

    grid = (Z * H * M,)

    _decoding_attn_stats_kernel[grid](
        Q, K, M_stat, L_stat,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        M_stat.stride(0), M_stat.stride(1), M_stat.stride(2),
        L_stat.stride(0), L_stat.stride(1), L_stat.stride(2),
        Z, H, M, N, Dq, scale,
    )

    O = torch.empty((Z, H, M, Dv), dtype=V.dtype, device=device)

    _decoding_attn_out_kernel_v2[grid](
        Q, K, V, O, M_stat, L_stat,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        M_stat.stride(0), M_stat.stride(1), M_stat.stride(2),
        L_stat.stride(0), L_stat.stride(1), L_stat.stride(2),
        Z, H, M, N, Dq, Dv, scale,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
