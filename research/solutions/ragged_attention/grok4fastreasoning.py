import torch
import triton
import triton.language as tl
import math
import inspect

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, row_lens,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    stride_rl,
    M: tl.constexpr, N: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr, BD: tl.constexpr, BDV: tl.constexpr
):
    pid_m = tl.program_id(0)
    offsets_m = pid_m * BM + tl.arange(0, BM)
    mask_m = offsets_m < M

    # Load Q block (BM, BD)
    offsets_d = tl.arange(0, BD)
    q_ptrs = Q + offsets_m[:, None] * stride_qm + offsets_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)

    # Load row_lens (BM,)
    rl_offsets = offsets_m * stride_rl
    row_lens_block = tl.load(row_lens + rl_offsets, mask=mask_m, other=0, dtype=tl.int64)

    # Initialize
    row_max = tl.full((BM,), float("-inf"), dtype=tl.float32)
    row_sum = tl.zeros((BM,), dtype=tl.float32)
    o_acc = tl.zeros((BM, BDV), dtype=tl.float32)

    # Loop over N blocks
    n_block = 0
    while True:
        n_start = n_block * BN
        if n_start >= N:
            break

        offsets_n = tl.arange(0, BN)
        mask_n = n_start + offsets_n < N
        global_n = n_start + offsets_n

        # Load K block (BD, BN)
        k_ptrs = K + offsets_n[None, :] * stride_km + offsets_d[:, None] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0, dtype=tl.float32)

        # Compute scores (BM, BN)
        scores = tl.dot(q, k)

        # Mask
        mask_m_n = (row_lens_block[:, None] > global_n[None, :]) & mask_n[None, :]
        scores_masked = tl.where(mask_m_n, scores, float("-inf"))
        m_block = tl.max(scores_masked, axis=1)

        row_max_new = tl.maximum(row_max, m_block)
        exp_diff = tl.where(row_max_new == float("-inf"), 1.0, tl.exp(row_max - row_max_new))

        # Exp scores for block
        exp_scores = tl.where(mask_m_n, tl.exp(scores - row_max_new[:, None]), 0.0)
        s_block = tl.sum(exp_scores, axis=1)

        old_s_rel = row_sum * exp_diff
        new_row_sum = old_s_rel + s_block

        # Load V block (BN, BDV)
        offsets_dv = tl.arange(0, BDV)
        v_ptrs = V + offsets_n[:, None] * stride_vm + offsets_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

        # P block
        p_block = tl.where(new_row_sum[:, None] > 0, exp_scores / new_row_sum[:, None], 0.0)

        # Contrib
        contrib = tl.dot(p_block, v)

        # Rescale and add
        scale_o = tl.where(new_row_sum > 0, old_s_rel / new_row_sum, 0.0)
        o_acc = o_acc * scale_o[:, None] + contrib

        # Update
        row_max = row_max_new
        row_sum = new_row_sum

        n_block += 1

    # Store O
    o_ptrs = O + offsets_m[:, None] * stride_om + offsets_dv[None, :] * stride_od
    tl.store(o_ptrs, o_acc.to(tl.float16), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    Dv = V.shape[1]
    scale = 1.0 / math.sqrt(D)
    O = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)

    BM = 64
    BN = 128
    BD = 64
    BDV = 64

    grid = lambda meta: (triton.cdiv(M, meta['BM']), )

    row_lens = row_lens.to(torch.int64)

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        row_lens.stride(0),
        M, N,
        BM=BM, BN=BN, BD=BD, BDV=BDV
    )

    return O
"""
        return {"code": code}