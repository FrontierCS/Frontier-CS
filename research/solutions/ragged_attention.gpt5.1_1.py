import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, ROW_LENS, O,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    m_mask = offs_m < M
    d_mask = offs_d < D
    dv_mask = offs_dv < Dv

    # Load Q block [BLOCK_M, D]
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None] & d_mask[None, :], other=0.0)
    q = q.to(tl.float32)

    # Load row lengths
    row_len = tl.load(ROW_LENS + offs_m, mask=m_mask, other=0)
    row_len = row_len.to(tl.int32)

    NEG_INF = -1.0e9

    # Streaming softmax state
    m_i = tl.full([BLOCK_M], NEG_INF, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Loop over K/V blocks
    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K block [BLOCK_N, D]
        k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & d_mask[None, :], other=0.0)
        k = k.to(tl.float32)

        # Compute QK^T
        qk = tl.dot(q, tl.trans(k))
        qk = qk * sm_scale

        # Ragged + bounds mask
        # valid if: row index valid, key index within N, key index < row_len[row]
        valid_len = offs_n[None, :] < row_len[:, None]
        attn_mask = m_mask[:, None] & n_mask[None, :] & valid_len
        scores = tl.where(attn_mask, qk, NEG_INF)

        # Streaming softmax update
        current_max = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, current_max)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new[:, None])
        l_new = l_i * alpha + tl.sum(p, axis=1)
        inv_l_new = 1.0 / l_new
        prev_factor = l_i * alpha * inv_l_new
        acc = acc * prev_factor[:, None]

        # Load V block [BLOCK_N, Dv]
        v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0)
        v = v.to(tl.float32)

        contrib = tl.dot(p, v)
        acc = acc + contrib * inv_l_new[:, None]

        m_i = m_new
        l_i = l_new
        start_n += BLOCK_N

    # Store output
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    # Fallback to PyTorch implementation for unsupported cases
    def _fallback(Q, K, V, row_lens):
        M, D = Q.shape
        N = K.shape[0]
        Dv = V.shape[1]
        scale = 1.0 / math.sqrt(float(D))
        Qf = Q.to(torch.float32)
        Kf = K.to(torch.float32)
        Vf = V.to(torch.float32)
        O = torch.zeros((M, Dv), device=Q.device, dtype=torch.float32)
        for i in range(M):
            L = int(row_lens[i].item())
            if L <= 0:
                continue
            scores = (Qf[i] @ Kf[:L].T) * scale
            probs = torch.softmax(scores, dim=-1)
            O[i] = probs @ Vf[:L]
        return O.to(torch.float16)

    if Q.device.type != "cuda" or K.device.type != "cuda" or V.device.type != "cuda":
        return _fallback(Q, K, V, row_lens)

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.is_contiguous()
    assert K.is_contiguous()
    assert V.is_contiguous()

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape
    assert D == Dk, "Q and K must have same feature dimension"
    assert N == Nv, "K and V must have same number of rows"
    if D > 64 or Dv > 64:
        return _fallback(Q, K, V, row_lens)

    row_lens_i32 = row_lens.to(device=Q.device, dtype=torch.int32).contiguous()

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    grid = (triton.cdiv(M, BLOCK_M),)
    sm_scale = 1.0 / math.sqrt(float(D))

    _ragged_attn_fwd_kernel[grid](
        Q, K, V, row_lens_i32, O,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O
"""
        return {"code": code}