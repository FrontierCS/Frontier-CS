class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def kernel(
    q, k, v, o,
    M: tl.int32,
    N: tl.int32,
    D_Q: tl.int32,
    D_V: tl.int32,
    scale: tl.float32,
    causal: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DQ: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    block_start_m = pid_m * BLOCK_M
    offs_m = block_start_m + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    mask_dq = tl.arange(0, BLOCK_DQ) < D_Q
    mask_dv = tl.arange(0, BLOCK_DV) < D_V

    q_offsets = (block_start_m, 0)
    q_ptrs = tl.make_block_ptr(
        base=q,
        shape=(M, D_Q),
        offsets=q_offsets,
        block_shape=(BLOCK_M, BLOCK_DQ),
        order=(0, 1)
    )
    q_block = tl.load(q_ptrs, mask=(mask_m[:, None], mask_dq[None, :]), other=0.0).to(tl.float32)

    m_acc = tl.full((BLOCK_M,), -1e4, dtype=tl.float32)
    l_acc = tl.zeros((BLOCK_M,), dtype=tl.float32)
    o_acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    num_kv_blocks = (N + BLOCK_N - 1) // BLOCK_N
    curr_kv = tl.tensor([0], dtype=tl.int32)
    while curr_kv[0] < num_kv_blocks:
        block_start_n = curr_kv[0] * BLOCK_N
        offs_n = block_start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_offsets = (block_start_n, 0)
        k_ptrs = tl.make_block_ptr(
            base=k,
            shape=(N, D_Q),
            offsets=k_offsets,
            block_shape=(BLOCK_N, BLOCK_DQ),
            order=(0, 1)
        )
        k_block = tl.load(k_ptrs, mask=(mask_n[:, None], mask_dq[None, :]), other=0.0).to(tl.float32)

        v_offsets = (block_start_n, 0)
        v_ptrs = tl.make_block_ptr(
            base=v,
            shape=(N, D_V),
            offsets=v_offsets,
            block_shape=(BLOCK_N, BLOCK_DV),
            order=(0, 1)
        )
        v_block = tl.load(v_ptrs, mask=(mask_n[:, None], mask_dv[None, :]), other=0.0).to(tl.float32)

        s = tl.dot(q_block, tl.trans(k_block)) * scale

        if causal:
            row_idx = block_start_m + tl.arange(0, BLOCK_M)
            col_idx = block_start_n + tl.arange(0, BLOCK_N)
            mask_causal = col_idx[None, :] > row_idx[:, None]
            s = tl.where(mask_causal, -1e4, s)

        m_kv = tl.max(s, 1)
        p = tl.exp(s - m_kv[:, None])
        l_kv = tl.sum(p, 1)

        m_new = tl.maximum(m_acc, m_kv)
        alpha = tl.exp(m_acc - m_new)
        beta = tl.exp(m_kv - m_new)
        l_new = alpha * l_acc + beta * l_kv

        p_v = tl.dot(p, v_block)
        o_new = alpha[:, None] * o_acc + beta[:, None] * p_v

        m_acc = m_new
        l_acc = l_new
        o_acc = o_new

        curr_kv[0] += 1

    row_scale = tl.where(l_acc > 0, 1.0 / l_acc, 0.0)
    o_normalized = o_acc * row_scale[:, None]

    o_offsets = (block_start_m, 0)
    o_ptrs = tl.make_block_ptr(
        base=o,
        shape=(M, D_V),
        offsets=o_offsets,
        block_shape=(BLOCK_M, BLOCK_DV),
        order=(0, 1)
    )
    tl.store(o_ptrs, o_normalized.to(tl.float16), mask=(mask_m[:, None], mask_dv[None, :]))

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D_Q = Q.shape
    _, _, N, D_V = V.shape
    assert K.shape[2] == N and K.shape[3] == D_Q
    scale = 1 / math.sqrt(D_Q)
    output = torch.empty((Z, H, M, D_V), dtype=Q.dtype, device=Q.device)

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DQ = 64
    BLOCK_DV = 64

    for z in range(Z):
        for h in range(H):
            q_2d = Q[z, h]
            k_2d = K[z, h]
            v_2d = V[z, h]
            o_2d = output[z, h]

            num_q_blocks = triton.cdiv(M, BLOCK_M)
            grid = (num_q_blocks,)
            kernel[grid](
                q_2d, k_2d, v_2d, o_2d,
                M, N, D_Q, D_V, scale,
                tl.constexpr(1) if causal else tl.constexpr(0),
                BLOCK_M=BLOCK_M,
                BLOCK_N=BLOCK_N,
                BLOCK_DQ=BLOCK_DQ,
                BLOCK_DV=BLOCK_DV
            )
    return output
"""
        return {"code": code}