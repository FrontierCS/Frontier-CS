import typing


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl
import math


@triton.jit
def _ragged_attn_fwd(
    Q, K, V, ROW_LENS, O,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    HEAD_DIM: tl.constexpr,
    VALUE_DIM: tl.constexpr,
    NUM_BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    offs_d = tl.arange(0, HEAD_DIM)
    offs_vd = tl.arange(0, VALUE_DIM)

    # Load row lengths for this block of queries
    row_lens = tl.load(ROW_LENS + offs_m, mask=m_mask, other=0)

    # Load block of Q: [BLOCK_M, HEAD_DIM]
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
    q = q.to(tl.float32)

    # Initialize streaming softmax state
    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, VALUE_DIM), tl.float32)

    for block_n in range(NUM_BLOCK_N):
        start_n = block_n * BLOCK_N
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load block of K: [HEAD_DIM, BLOCK_N]
        k_ptrs = K + offs_n[None, :] * stride_km + offs_d[:, None] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[None, :], other=0.0)
        k = k.to(tl.float32)

        # Compute attention logits
        logits = tl.dot(q, k) * scale  # [BLOCK_M, BLOCK_N]

        # Ragged masking: j < row_lens[i]
        key_idx = offs_n[None, :]              # [1, BLOCK_N]
        row_len_b = row_lens[:, None]          # [BLOCK_M, 1]
        attn_mask = key_idx < row_len_b
        full_mask = m_mask[:, None] & n_mask[None, :] & attn_mask

        logits = tl.where(full_mask, logits, float("-inf"))

        # Streaming softmax update
        row_max = tl.max(logits, axis=1)
        m_i_new = tl.maximum(m_i, row_max)

        logits_minus_m = logits - m_i_new[:, None]
        exp_logits = tl.exp(logits_minus_m)
        exp_logits = tl.where(full_mask, exp_logits, 0.0)

        l_new = tl.sum(exp_logits, axis=1)
        alpha = tl.exp(m_i - m_i_new)

        l_i = l_i * alpha + l_new

        # Load block of V: [BLOCK_N, VALUE_DIM]
        v_ptrs = V + offs_n[:, None] * stride_vm + offs_vd[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        v = v.to(tl.float32)

        pv = tl.dot(exp_logits, v)  # [BLOCK_M, VALUE_DIM]

        acc = acc * alpha[:, None] + pv
        m_i = m_i_new

    # Normalize accumulated values
    out = acc / l_i[:, None]

    # Write back output
    o_ptrs = O + offs_m[:, None] * stride_om + offs_vd[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    # Basic shape checks
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16 tensors"

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape

    assert D == Dk, "Q and K must have the same feature dimension"
    assert N == Nv, "K and V must have the same number of rows"
    assert row_lens.shape[0] == M, "row_lens must have length M"

    # Convert row_lens to int32
    if row_lens.dtype != torch.int32:
        row_lens32 = row_lens.to(torch.int32)
    else:
        row_lens32 = row_lens

    # Clamp row lengths to valid range [0, N]
    row_lens32 = torch.clamp(row_lens32, 0, N)

    # Allocate output
    O = torch.empty((M, Dv), dtype=torch.float16, device=Q.device)

    BLOCK_M = 64
    BLOCK_N = 64
    num_block_n = triton.cdiv(N, BLOCK_N)
    grid = (triton.cdiv(M, BLOCK_M),)

    scale = 1.0 / math.sqrt(D)

    _ragged_attn_fwd[grid](
        Q, K, V, row_lens32, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        HEAD_DIM=D,
        VALUE_DIM=Dv,
        NUM_BLOCK_N=num_block_n,
        num_warps=4,
        num_stages=2,
    )

    return O
"""
        return {"code": code}
