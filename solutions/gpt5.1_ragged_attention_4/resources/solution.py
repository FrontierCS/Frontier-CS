import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, ROW_LENS, O,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M,
    scale,
    N_CTX: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    # Load query row
    q_ptrs = Q + row * stride_qm + offs_d * stride_qd
    q = tl.load(q_ptrs, mask=offs_d < D_HEAD, other=0.0)
    q = q.to(tl.float32)

    # Load and clamp row length
    row_len = tl.load(ROW_LENS + row)
    row_len = tl.cast(row_len, tl.int32)
    row_len = tl.where(row_len < 0, 0, row_len)
    row_len = tl.where(row_len > N_CTX, N_CTX, row_len)

    # If no valid keys, output zeros
    if row_len == 0:
        o_ptrs = O + row * stride_om + offs_dv * stride_od
        zero = tl.zeros([D_VALUE], dtype=tl.float16)
        tl.store(o_ptrs, zero, mask=offs_dv < D_VALUE)
        return

    m_i = -float("inf")
    l_i = 0.0
    acc = tl.zeros([D_VALUE], dtype=tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        # Load K block: [BLOCK_N, D_HEAD]
        k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
        k = tl.load(
            k_ptrs,
            mask=mask_n[:, None] & (offs_d[None, :] < D_HEAD),
            other=0.0,
        )
        k = k.to(tl.float32)

        # Compute attention scores qk: [BLOCK_N]
        qk = tl.sum(k * q[None, :], axis=1)
        qk = qk * scale

        # Mask out positions beyond row_len
        mask_len = offs_n < row_len
        valid = mask_n & mask_len
        qk = tl.where(valid, qk, -float("inf"))

        # Streaming softmax update
        max_qk = tl.max(qk, axis=0)
        m_i_new = tl.where(max_qk > m_i, max_qk, m_i)

        p = tl.exp(qk - m_i_new)
        l_ij = tl.sum(p, axis=0)

        # Load V block: [BLOCK_N, D_VALUE]
        v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
        v = tl.load(
            v_ptrs,
            mask=mask_n[:, None] & (offs_dv[None, :] < D_VALUE),
            other=0.0,
        )
        v = v.to(tl.float32)

        # Weighted value sum: pv = p @ V_block : [D_VALUE]
        pv = tl.sum(v * p[:, None], axis=0)

        alpha = tl.exp(m_i - m_i_new)
        l_i_new = l_i * alpha + l_ij

        acc = acc * (l_i * alpha / l_i_new) + pv / l_i_new

        m_i = m_i_new
        l_i = l_i_new

    # Store result
    o_ptrs = O + row * stride_om + offs_dv * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=offs_dv < D_VALUE)


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape
    assert D == Dk
    assert N == Nv

    Q = Q.contiguous()
    K = K.contiguous()
    V = V.contiguous()

    # Ensure row_lens is int32 and clamped
    row_lens = row_lens.to(device=Q.device, dtype=torch.int32)
    row_lens = torch.clamp(row_lens, 0, N).contiguous()

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_N = 128
    scale = 1.0 / math.sqrt(D)

    grid = (M,)

    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M,
        scale,
        N_CTX=N,
        BLOCK_N=BLOCK_N,
        D_HEAD=D,
        D_VALUE=Dv,
        num_warps=4,
        num_stages=2,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import os
        return {"program_path": os.path.abspath(__file__)}
