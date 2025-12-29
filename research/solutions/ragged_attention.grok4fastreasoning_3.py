import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def ragged_kernel(
    Q, K, V, O, ROW_LENS, M, D, Dv, scale: tl.f32,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    q_offset = pid * D * 2
    q = tl.load(Q + q_offset).to(tl.float32)

    l_offset = pid * 4
    L = tl.load(ROW_LENS + l_offset).to(tl.int32)

    if L == 0:
        o_offset = pid * Dv * 2
        zero_vec = tl.zeros((Dv,), dtype=tl.float16)
        tl.store(O + o_offset, zero_vec)
        return

    # First pass: compute m and s
    m = tl.float32('-inf')
    s = tl.float32(0.0)
    start = tl.int32(0)
    while start < L:
        end = tl.minimum(start + BLOCK_N, L)
        bn = end - start

        # Load k_block
        row_offsets_k = (start + tl.arange(0, BLOCK_N)) * D * 2
        col_offsets_k = tl.arange(0, D) * 2
        k_offsets = row_offsets_k[:, None] + col_offsets_k[None, :]
        mask_k = (tl.arange(0, BLOCK_N)[:, None] < bn) & (tl.arange(0, D)[None, :] < D)
        k_block_f16 = tl.load(K + k_offsets, mask=mask_k, other=tl.float16(0.0))
        k_block = k_block_f16.to(tl.float32)

        scores = tl.sum(k_block * q[None, :], axis=1) * scale
        scores = tl.where(tl.arange(0, BLOCK_N) < bn, scores, tl.float32('-1e9'))

        m_block = tl.max(scores)
        m_new = tl.maximum(m, m_block)
        exp_old = tl.exp(m - m_new)
        exp_scores = tl.exp(scores - m_new)
        s_new = s * exp_old + tl.sum(exp_scores)
        m = m_new
        s = s_new

        start += BLOCK_N

    # Second pass: compute output
    o_acc = tl.zeros((Dv,), dtype=tl.float32)
    denom = s
    start = tl.int32(0)
    while start < L:
        end = tl.minimum(start + BLOCK_N, L)
        bn = end - start

        # Load k_block again
        row_offsets_k = (start + tl.arange(0, BLOCK_N)) * D * 2
        col_offsets_k = tl.arange(0, D) * 2
        k_offsets = row_offsets_k[:, None] + col_offsets_k[None, :]
        mask_k = (tl.arange(0, BLOCK_N)[:, None] < bn) & (tl.arange(0, D)[None, :] < D)
        k_block_f16 = tl.load(K + k_offsets, mask=mask_k, other=tl.float16(0.0))
        k_block = k_block_f16.to(tl.float32)

        scores = tl.sum(k_block * q[None, :], axis=1) * scale
        scores = tl.where(tl.arange(0, BLOCK_N) < bn, scores, tl.float32('-1e9'))

        # Load v_block
        row_offsets_v = (start + tl.arange(0, BLOCK_N)) * Dv * 2
        col_offsets_v = tl.arange(0, Dv) * 2
        v_offsets = row_offsets_v[:, None] + col_offsets_v[None, :]
        mask_v = (tl.arange(0, BLOCK_N)[:, None] < bn) & (tl.arange(0, Dv)[None, :] < Dv)
        v_block_f16 = tl.load(V + v_offsets, mask=mask_v, other=tl.float16(0.0))
        v_block = v_block_f16.to(tl.float32)

        probs = tl.exp(scores - m) / denom
        contrib = probs[:, None] * v_block
        o_acc += tl.sum(contrib, axis=0)

        start += BLOCK_N

    o_offset = pid * Dv * 2
    tl.store(O + o_offset, o_acc.to(tl.float16))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    output = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    scale = 1 / math.sqrt(D)
    row_lens_i32 = row_lens.to(torch.int32)
    BLOCK_N = 128
    ragged_kernel[grid=(M,)](Q, K, V, output, row_lens_i32, M, N, D, Dv, scale, BLOCK_N=BLOCK_N)
    return output
"""
        return {"code": code}