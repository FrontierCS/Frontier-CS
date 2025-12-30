import textwrap

CODE = textwrap.dedent('''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd(
    Q, K, V, Out,
    stride_qz, stride_qm, stride_qd,
    stride_kz, stride_kn, stride_kd,
    stride_vz, stride_vn, stride_vd,
    stride_oz, stride_om, stride_od,
    N_CTX, D_HEAD_Q, D_HEAD_V, scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL_Q: tl.constexpr, BLOCK_DMODEL_V: tl.constexpr,
    CAUSAL: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_m_blocks = tl.cdiv(N_CTX, BLOCK_M)
    batch_idx = pid // num_m_blocks
    m_block_idx = pid % num_m_blocks

    offs_m = m_block_idx * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n_init = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_DMODEL_Q)
    offs_dv = tl.arange(0, BLOCK_DMODEL_V)

    # Load Q: shape [BLOCK_M, D_HEAD_Q]
    q_ptrs = Q + batch_idx * stride_qz + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q_mask = (offs_m[:, None] < N_CTX) & (offs_dq[None, :] < D_HEAD_Q)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # Initialize softmax statistics and accumulator
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DMODEL_V), dtype=tl.float32)

    n_start = 0
    while n_start < N_CTX:
        offs_n = n_start + offs_n_init

        k_ptrs = K + batch_idx * stride_kz + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = V + batch_idx * stride_vz + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k_mask = (offs_n[:, None] < N_CTX) & (offs_dq[None, :] < D_HEAD_Q)
        v_mask = (offs_n[:, None] < N_CTX) & (offs_dv[None, :] < D_HEAD_V)

        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float32)

        # Compute attention scores [BLOCK_M, BLOCK_N]
        qk = tl.dot(q, tl.trans(k)) * scale

        # Apply padding and (optional) causal mask
        valid_m = offs_m < N_CTX
        valid_n = offs_n < N_CTX

        qk = tl.where(valid_n[None, :], qk, float("-inf"))
        qk = tl.where(valid_m[:, None], qk, float("-inf"))

        if CAUSAL:
            causal_mask = offs_m[:, None] >= offs_n[None, :]
            qk = tl.where(causal_mask, qk, float("-inf"))

        # Numerically-stable streaming softmax
        m_ij = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None] + tl.dot(p, v)
        m_i = m_i_new

        n_start += BLOCK_N

    # Normalize and store result
    o = acc / l_i[:, None]
    out_ptrs = Out + batch_idx * stride_oz + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    out_mask = (offs_m[:, None] < N_CTX) & (offs_dv[None, :] < D_HEAD_V)
    tl.store(out_ptrs, o.to(tl.float16), mask=out_mask)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.

    Args:
        Q: (Z, H, M, Dq) float16 CUDA tensor
        K: (Z, H, N, Dq) float16 CUDA tensor
        V: (Z, H, N, Dv) float16 CUDA tensor
        causal: whether to apply causal masking
    Returns:
        (Z, H, M, Dv) float16 CUDA tensor
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"

    Z, H, M, Dq = Q.shape
    zk, hk, N, Dk = K.shape
    zv, hv, Nv, Dv = V.shape
    assert Z == zk == zv and H == hk == hv, "Batch/head dimensions must match"
    assert N == M and Nv == N, "Sequence lengths must satisfy N == M"
    assert Dk == Dq, "Key dimension must match query dimension"

    # Flatten batch and heads into a single dimension
    BH = Z * H
    Q_ = Q.contiguous().view(BH, M, Dq)
    K_ = K.contiguous().view(BH, N, Dq)
    V_ = V.contiguous().view(BH, N, Dv)
    O_ = torch.empty((BH, M, Dv), device=Q.device, dtype=torch.float16)

    # Strides
    stride_qz, stride_qm, stride_qd = Q_.stride()
    stride_kz, stride_kn, stride_kd = K_.stride()
    stride_vz, stride_vn, stride_vd = V_.stride()
    stride_oz, stride_om, stride_od = O_.stride()

    head_dim_q = Dq
    head_dim_v = Dv

    if head_dim_q > 128 or head_dim_v > 128:
        raise ValueError("Head dimensions larger than 128 are not supported by this kernel")

    # Choose block sizes
    BLOCK_DMODEL_Q = 64 if head_dim_q <= 64 else 128
    BLOCK_DMODEL_V = 64 if head_dim_v <= 64 else 128
    BLOCK_M = 64
    BLOCK_N = 64

    num_m_blocks = triton.cdiv(M, BLOCK_M)
    grid = (BH * num_m_blocks,)

    scale = 1.0 / math.sqrt(head_dim_q)

    _flash_attn_fwd[grid](
        Q_, K_, V_, O_,
        stride_qz, stride_qm, stride_qd,
        stride_kz, stride_kn, stride_kd,
        stride_vz, stride_vn, stride_vd,
        stride_oz, stride_om, stride_od,
        M, head_dim_q, head_dim_v, scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL_Q=BLOCK_DMODEL_Q,
        BLOCK_DMODEL_V=BLOCK_DMODEL_V,
        CAUSAL=causal,
        num_warps=4,
        num_stages=2,
    )

    return O_.view(Z, H, M, Dv)
''')

# Execute the kernel code in this module's namespace so flash_attn is available here too
exec_globals = globals()
exec(CODE, exec_globals)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": CODE}