import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd(
    Q, K, V, ROW_LENS, O,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, DV,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    NUM_BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, BLOCK_DMODEL)
    mask_d = offs_d < D

    # Load Q for this block of rows
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    q = q.to(tl.float32)

    # Load row lengths
    row_lens = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)

    m_i = tl.full((BLOCK_M,), -1.0e9, dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    neg_inf = -1.0e9

    for block_idx in range(0, NUM_BLOCK_N):
        start_n = block_idx * BLOCK_N
        k_idx = start_n + offs_n
        mask_n = k_idx < N

        # Load K block
        k_ptrs = K + (k_idx[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        k = k.to(tl.float32)

        # Load V block
        v_ptrs = V + (k_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v_mask = mask_n[:, None] & (offs_dv[None, :] < DV)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        v = v.to(tl.float32)

        # Compute QK^T
        qk = tl.dot(q, tl.trans(k))
        qk = qk * scale

        # Ragged masking: each row attends only up to row_lens[i]
        row_lens_b = row_lens[:, None]
        k_idx_b = k_idx[None, :]
        mask_len = k_idx_b < row_lens_b
        valid_mask = mask_m[:, None] & mask_n[None, :] & mask_len

        qk = tl.where(valid_mask, qk, neg_inf)

        # Streaming softmax update
        m_curr = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_curr)

        exp_m_i = tl.exp(m_i - m_new)

        exp_qk = tl.exp(qk - m_new[:, None])
        p = tl.where(valid_mask, exp_qk, 0.0)

        l_new = l_i * exp_m_i + tl.sum(p, axis=1)
        l_new_safe = tl.where(l_new == 0.0, 1.0, l_new)

        acc = acc * (l_i * exp_m_i / l_new_safe)[:, None] + tl.dot(p, v) / l_new_safe[:, None]

        m_i = m_new
        l_i = l_new

    # Write back output
    o_ptrs = O + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    o_mask = mask_m[:, None] & (offs_dv[None, :] < DV)
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16

    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert N == Nv and D == Dk

    row_lens_i32 = row_lens.to(device=Q.device, dtype=torch.int32)

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64

    def next_power_of_2(x: int) -> int:
        return 1 if x == 0 else 2 ** ((x - 1).bit_length())

    BLOCK_DMODEL = min(128, next_power_of_2(D))
    BLOCK_DV = min(128, next_power_of_2(DV))

    grid = (triton.cdiv(M, BLOCK_M),)

    scale = 1.0 / (D ** 0.5)
    num_block_n = triton.cdiv(N, BLOCK_N)

    _ragged_attn_fwd[grid](
        Q, K, V, row_lens_i32, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, DV,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        NUM_BLOCK_N=num_block_n,
        num_warps=4,
        num_stages=2,
    )

    return O
'''
        return {"code": code}