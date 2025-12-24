import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd(
    Q, K, V, Out,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_ob, stride_om, stride_od,
    B, M, N, D_HEAD, D_VALUE, sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_n_init = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    row_mask = offs_m < M
    dq_mask = offs_d < D_HEAD

    # Load Q block [BLOCK_M, BLOCK_DMODEL]
    q_ptrs = Q + pid_b * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None] & dq_mask[None, :], other=0.0)
    q = q.to(tl.float32)

    NEG_INF = -1.0e9
    m_i = tl.full((BLOCK_M,), NEG_INF, tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_n_init
        col_mask = offs_n < N

        # K block [BLOCK_N, BLOCK_DMODEL]
        k_ptrs = K + pid_b * stride_kb + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=col_mask[:, None] & dq_mask[None, :], other=0.0)
        k = k.to(tl.float32)

        # V block [BLOCK_N, BLOCK_DV]
        dv_mask = offs_dv < D_VALUE
        v_ptrs = V + pid_b * stride_vb + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=col_mask[:, None] & dv_mask[None, :], other=0.0)
        v = v.to(tl.float32)

        # Attention scores [BLOCK_M, BLOCK_N]
        qk = tl.dot(q, tl.trans(k)) * sm_scale

        # Base mask for sequence bounds
        mask = row_mask[:, None] & col_mask[None, :]

        # Causal mask if requested
        if causal:
            q_idx = offs_m[:, None]
            k_idx = offs_n[None, :]
            causal_mask = k_idx <= q_idx
            mask = mask & causal_mask

        qk = tl.where(mask, qk, NEG_INF)

        # Streaming softmax
        m_ij = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_i_new[:, None])
        l_ij = tl.sum(p, axis=1)
        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + l_ij
        acc = acc * alpha[:, None] + tl.dot(p, v)
        m_i = m_i_new

    # Normalize
    out = acc / l_i[:, None]

    # Store result
    dv_mask = offs_dv < D_VALUE
    out_ptrs = Out + pid_b * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, out, mask=row_mask[:, None] & dv_mask[None, :])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.

    Args:
        Q: (Z, H, M, Dq) float16
        K: (Z, H, N, Dq) float16
        V: (Z, H, N, Dv) float16
        causal: bool

    Returns:
        (Z, H, M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.device == K.device == V.device, "All inputs must be on the same device"

    Z, H, M, D_HEAD = Q.shape
    Zk, Hk, N, D_HEAD_k = K.shape
    Zv, Hv, N_v, D_VALUE = V.shape

    assert Z == Zk == Zv, "Batch dimension mismatch"
    assert H == Hk == Hv, "Head dimension mismatch"
    assert N == M == N_v, "Sequence length mismatch"
    assert D_HEAD == D_HEAD_k, "Q/K head dimension mismatch"

    B = Z * H

    Q_ = Q.reshape(B, M, D_HEAD)
    K_ = K.reshape(B, N, D_HEAD)
    V_ = V.reshape(B, N, D_VALUE)

    def next_power_of_2(x: int) -> int:
        y = 1
        while y < x:
            y <<= 1
        return y

    BLOCK_DMODEL = next_power_of_2(D_HEAD)
    BLOCK_DV = next_power_of_2(D_VALUE)

    # Cap to keep register usage reasonable
    if BLOCK_DMODEL > 256:
        BLOCK_DMODEL = 256
    if BLOCK_DV > 256:
        BLOCK_DV = 256

    # Sequence blocking
    if M <= 64:
        BLOCK_M = 32
        BLOCK_N = 64
    else:
        BLOCK_M = 64
        BLOCK_N = 64

    sm_scale = 1.0 / (D_HEAD ** 0.5)

    Out = torch.empty((B, M, D_VALUE), device=Q.device, dtype=torch.float16)

    grid = (triton.cdiv(M, BLOCK_M), B)

    _flash_attn_fwd[grid](
        Q_, K_, V_, Out,
        Q_.stride(0), Q_.stride(1), Q_.stride(2),
        K_.stride(0), K_.stride(1), K_.stride(2),
        V_.stride(0), V_.stride(1), V_.stride(2),
        Out.stride(0), Out.stride(1), Out.stride(2),
        B, M, N, D_HEAD, D_VALUE, sm_scale,
        causal=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return Out.reshape(Z, H, M, D_VALUE)
'''
        )
        return {"code": code}
