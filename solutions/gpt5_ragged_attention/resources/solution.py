import math
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, ROW_LENS, O,
    M, N,
    stride_qm, stride_qk,
    stride_km, stride_kk,
    stride_vm, stride_vk,
    stride_om, stride_ok,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    HEAD_DIM: tl.constexpr,
    VALUE_DIM: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, HEAD_DIM)
    offs_dv = tl.arange(0, VALUE_DIM)

    # Load row lengths per query row
    lens = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)

    # Load Q block
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)

    # Accumulators
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, VALUE_DIM], dtype=tl.float32)

    # Iterate over K/V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K and V tiles
        k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kk
        v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vk

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        # Compute attention scores
        qk = tl.dot(q, tl.trans(k)).to(tl.float32)
        qk = qk * scale

        # Mask out positions beyond row_len and out-of-bounds
        valid = (offs_n[None, :] < lens[:, None]) & mask_n[None, :] & mask_m[:, None]
        qk = tl.where(valid, qk, -float('inf'))

        # Streaming softmax update
        row_max = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, row_max)

        s = tl.exp(m_i - m_i_new)
        s = tl.where(mask_m, s, 0.0)

        p = tl.exp(qk - m_i_new[:, None])
        p = tl.where(mask_m[:, None], p, 0.0)

        l_i = l_i * s + tl.sum(p, axis=1)
        acc = acc * s[:, None] + tl.dot(p, v)

        m_i = m_i_new

    # Normalize
    inv_l = 1.0 / l_i
    inv_l = tl.where(mask_m, inv_l, 0.0)
    out = acc * inv_l[:, None]
    out = out.to(tl.float16)

    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ok
    tl.store(o_ptrs, out, mask=mask_m[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.

    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)

    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype in (torch.float16, torch.bfloat16) and V.dtype in (torch.float16, torch.bfloat16), "Q, K, V must be float16 or bfloat16"
    assert Q.shape[1] == K.shape[1], "Q and K must have same feature dimension"
    assert K.shape[0] == V.shape[0], "K and V must have same number of rows"
    assert Q.shape[0] == row_lens.shape[0], "row_lens length must match M"

    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]

    # Ensure types and contiguity
    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    rl = row_lens.contiguous()

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    # Choose block sizes and launch params
    BLOCK_M = 128 if M >= 128 else 64
    BLOCK_N = 64
    # Scale
    scale = 1.0 / math.sqrt(float(D))

    grid = (triton.cdiv(M, BLOCK_M),)

    num_warps = 4 if (BLOCK_M == 64) else 8
    num_stages = 2

    _ragged_attn_kernel[grid](
        Qc, Kc, Vc, rl, O,
        M, N,
        Qc.stride(0), Qc.stride(1),
        Kc.stride(0), Kc.stride(1),
        Vc.stride(0), Vc.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        HEAD_DIM=D, VALUE_DIM=Dv,
        num_warps=num_warps, num_stages=num_stages,
    )
    return O
'''
        return {"code": textwrap.dedent(code)}
