import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
import math

@triton.jit
def kernel(
    Q_PTR, K_PTR, V_PTR, ROW_LENS_PTR, O_PTR,
    M: tl.int32,
    N: tl.int32,
    D: tl.int32,
    Dv: tl.int32,
    scale: tl.float32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_M
    offsets = block_start + tl.arange(0, BLOCK_M)
    mask = offsets < M

    # Load Q block
    q_offsets = offsets[:, None] * D + tl.arange(0, D)[None, :]
    Q_block = tl.load(Q_PTR + q_offsets, dtype=tl.float16, mask=mask[:, None], other=0.0).to(tl.float32)

    # Load row_lens
    rl_offsets = offsets
    row_lens_block = tl.load(ROW_LENS_PTR + rl_offsets, dtype=tl.int32, mask=mask, other=0)

    # Initialize online softmax stats
    m = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)

    # Loop over key tiles
    for start_n in range(0, N, BLOCK_N):
        end_n = tl.minimum(N, start_n + BLOCK_N)
        offsets_n = tl.arange(0, end_n - start_n)
        block_n = end_n - start_n

        # Load K tile
        k_offsets = (start_n + offsets_n)[:, None] * D + tl.arange(0, D)[None, :]
        K_tile = tl.load(K_PTR + k_offsets, dtype=tl.float16, other=0.0).to(tl.float32)

        # Load V tile
        v_offsets = (start_n + offsets_n)[:, None] * Dv + tl.arange(0, Dv)[None, :]
        V_tile = tl.load(V_PTR + v_offsets, dtype=tl.float16, other=0.0).to(tl.float32)

        # Compute attention scores
        scores = tl.sum(Q_block[:, None, :] * K_tile[None, :, :], axis=2) * scale

        # Apply masking
        j_offsets = start_n + offsets_n
        mask_j = j_offsets[None, :] >= row_lens_block[:, None]
        scores = tl.where(mask_j, -10000.0, scores)

        # Online softmax update
        m_tile = tl.max(scores, axis=1)
        m_new = tl.maximum(m, m_tile)
        alpha = tl.exp(m - m_new)
        p = tl.exp(scores - m_new[:, None])
        l_new = alpha * l + tl.sum(p, axis=1)

        # Compute partial output
        partial_o = tl.sum(p[:, :, None] * V_tile[None, :, :], axis=1)

        # Update output accumulator
        o_scale = l * alpha
        o = (o * o_scale[:, None] + partial_o) / l_new[:, None]

        # Update stats
        l = l_new
        m = m_new

    # Store output
    o_offsets = offsets[:, None] * Dv + tl.arange(0, Dv)[None, :]
    tl.store(O_PTR + o_offsets, o.to(tl.float16), mask=mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    scale = 1.0 / math.sqrt(D)
    O = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    BLOCK_M = 64
    BLOCK_N = 64
    grid = (triton.cdiv(M, BLOCK_M),)
    row_lens = row_lens.to(torch.int32)
    kernel[grid](
        Q, K, V, row_lens, O,
        M, N, D, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
    )
    return O
'''
        return {"code": code}