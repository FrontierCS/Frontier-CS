import math
import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qm, stride_qd,
    stride_kz, stride_kn, stride_kd,
    stride_vz, stride_vn, stride_vd,
    stride_gqz, stride_gqm, stride_gqd,
    stride_gkz, stride_gkn, stride_gkd,
    stride_oz, stride_om, stride_od,
    ZH, M, N, Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    m_mask = offs_m < M
    dv_mask = offs_dv < Dv

    # initialize softmax statistics
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    # iterate over K/V blocks
    n_start = 0
    while n_start < N:
        offs_n_cur = n_start + offs_n
        n_mask = offs_n_cur < N

        # compute attention scores for current K/V block
        s = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        d_start = 0
        while d_start < Dq:
            offs_d_cur = d_start + offs_d
            d_mask = offs_d_cur < Dq

            # Load Q and GQ tiles [BM, BD]
            q_ptrs = Q_ptr + pid_zh * stride_qz + (offs_m[:, None] * stride_qm) + (offs_d_cur[None, :] * stride_qd)
            gq_ptrs = GQ_ptr + pid_zh * stride_gqz + (offs_m[:, None] * stride_gqm) + (offs_d_cur[None, :] * stride_gqd)
            q = tl.load(q_ptrs, mask=(m_mask[:, None] & d_mask[None, :]), other=0.).to(tl.float16)
            gq = tl.load(gq_ptrs, mask=(m_mask[:, None] & d_mask[None, :]), other=0.)
            gate_q = tl.sigmoid(gq).to(q.dtype)
            qg = q * gate_q  # [BM, BD], fp16

            # Load K and GK tiles [BN, BD]
            k_ptrs = K_ptr + pid_zh * stride_kz + (offs_n_cur[:, None] * stride_kn) + (offs_d_cur[None, :] * stride_kd)
            gk_ptrs = GK_ptr + pid_zh * stride_gkz + (offs_n_cur[:, None] * stride_gkn) + (offs_d_cur[None, :] * stride_gkd)
            k = tl.load(k_ptrs, mask=(n_mask[:, None] & d_mask[None, :]), other=0.).to(tl.float16)
            gk = tl.load(gk_ptrs, mask=(n_mask[:, None] & d_mask[None, :]), other=0.)
            gate_k = tl.sigmoid(gk).to(k.dtype)
            kg = k * gate_k  # [BN, BD], fp16

            # Accumulate scores: [BM, BN] += [BM, BD] @ [BD, BN]
            s += tl.dot(qg, tl.trans(kg)).to(tl.float32)
            d_start += BLOCK_DMODEL

        # scale
        s = s * scale

        # mask out invalid n columns by setting to very negative
        neg_large = tl.full((1,), -1.0e30, dtype=tl.float32)
        s = tl.where(n_mask[None, :], s, neg_large)

        # Update streaming softmax stats
        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        # Compute p = exp(s - m_new)
        p = tl.exp(s - m_new[:, None])
        # Compute l_i update
        l_update = tl.sum(p, axis=1)
        alpha = tl.exp(m_i - m_new)

        # Load V block [BN, DV]
        v_ptrs = V_ptr + pid_zh * stride_vz + (offs_n_cur[:, None] * stride_vn) + (offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=(n_mask[:, None] & dv_mask[None, :]), other=0.).to(tl.float16)

        # Accumulate output: acc = acc * alpha + p @ v
        acc = acc * alpha[:, None] + tl.dot(p, v).to(tl.float32)

        # Update m_i, l_i
        l_i = l_i * alpha + l_update
        m_i = m_new

        n_start += BLOCK_N

    # Normalize
    out = acc / l_i[:, None]
    # Store
    o_ptrs = O_ptr + pid_zh * stride_oz + (offs_m[:, None] * stride_om) + (offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, out.to(tl.float16), mask=(m_mask[:, None] & dv_mask[None, :]))


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.

    Args:
        Q: (Z, H, M, Dq) float16, CUDA
        K: (Z, H, N, Dq) float16, CUDA
        V: (Z, H, N, Dv) float16, CUDA
        GQ: (Z, H, M, Dq) float16, CUDA
        GK: (Z, H, N, Dq) float16, CUDA
    Returns:
        (Z, H, M, Dv) float16, CUDA
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
    Z, H, M, Dq = Q.shape
    Z2, H2, N, Dq2 = K.shape
    assert Z == Z2 and H == H2 and Dq == Dq2
    Z3, H3, N2, Dv = V.shape
    assert Z == Z3 and H == H3 and N == N2
    Z4, H4, M2, Dq3 = GQ.shape
    Z5, H5, N3, Dq4 = GK.shape
    assert Z == Z4 == Z5 and H == H4 == H5 and M == M2 and N == N3 and Dq == Dq3 == Dq4

    device = Q.device
    ZH = Z * H

    # Flatten (Z, H) -> (ZH,)
    Q_ = Q.contiguous().view(ZH, M, Dq)
    K_ = K.contiguous().view(ZH, N, Dq)
    V_ = V.contiguous().view(ZH, N, Dv)
    GQ_ = GQ.contiguous().view(ZH, M, Dq)
    GK_ = GK.contiguous().view(ZH, N, Dq)

    O = torch.empty((ZH, M, Dv), device=device, dtype=torch.float16)

    # Strides in elements
    stride_qz, stride_qm, stride_qd = Q_.stride()
    stride_kz, stride_kn, stride_kd = K_.stride()
    stride_vz, stride_vn, stride_vd = V_.stride()
    stride_gqz, stride_gqm, stride_gqd = GQ_.stride()
    stride_gkz, stride_gkn, stride_gkd = GK_.stride()
    stride_oz, stride_om, stride_od = O.stride()

    # Tiling parameters
    # Choose block sizes
    def next_power_of_2(x):
        return 1 if x <= 1 else 2 ** ((x - 1).bit_length())

    BLOCK_M = 64
    BLOCK_N = 64
    # Head dimension blocking
    BLOCK_DMODEL = 64 if Dq >= 64 else 32
    if Dq > 64 and Dq <= 128:
        BLOCK_DMODEL = 64
    elif Dq > 128:
        BLOCK_DMODEL = 128
    # Value dimension blocking: support up to 128 without loops
    BLOCK_DV = min(128, next_power_of_2(Dv))
    if BLOCK_DV < 32:
        BLOCK_DV = 32

    grid = (ZH, triton.cdiv(M, BLOCK_M))

    scale = 1.0 / math.sqrt(Dq)

    gdpa_fwd_kernel[grid](
        Q_, K_, V_, GQ_, GK_, O,
        stride_qz, stride_qm, stride_qd,
        stride_kz, stride_kn, stride_kd,
        stride_vz, stride_vn, stride_vd,
        stride_gqz, stride_gqm, stride_gqd,
        stride_gkz, stride_gkn, stride_gkd,
        stride_oz, stride_om, stride_od,
        ZH, M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4 if (BLOCK_M == 64 and BLOCK_N == 64) else 8,
        num_stages=2,
    )

    return O.view(Z, H, M, Dv)
'''
        return {"code": code}
