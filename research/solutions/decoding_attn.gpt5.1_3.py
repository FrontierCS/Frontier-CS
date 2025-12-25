import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_N': 64, 'BLOCK_D_HEAD': 64, 'BLOCK_DV': 64},
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 128, 'BLOCK_D_HEAD': 64, 'BLOCK_DV': 64},
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 256, 'BLOCK_D_HEAD': 64, 'BLOCK_DV': 64},
            num_warps=8,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 128, 'BLOCK_D_HEAD': 64, 'BLOCK_DV': 64},
            num_warps=8,
            num_stages=3,
        ),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_q_z, stride_q_h, stride_q_m, stride_q_d,
    stride_k_z, stride_k_h, stride_k_n, stride_k_d,
    stride_v_z, stride_v_h, stride_v_n, stride_v_d,
    stride_o_z, stride_o_h, stride_o_m, stride_o_d,
    Z, H, M, N, Dq, Dv,
    SCALE,
    BLOCK_N: tl.constexpr,
    BLOCK_D_HEAD: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    # Base pointers
    q_ptr = Q_ptr + z_idx * stride_q_z + h_idx * stride_q_h + m_idx * stride_q_m
    k_head_ptr = K_ptr + z_idx * stride_k_z + h_idx * stride_k_h
    v_head_ptr = V_ptr + z_idx * stride_v_z + h_idx * stride_v_h
    o_ptr = O_ptr + z_idx * stride_o_z + h_idx * stride_o_h + m_idx * stride_o_m

    d_q = tl.arange(0, BLOCK_D_HEAD)
    q_mask = d_q < Dq
    q = tl.load(q_ptr + d_q * stride_q_d, mask=q_mask, other=0.0)
    q = q.to(tl.float32)

    d_v = tl.arange(0, BLOCK_DV)
    n_offsets = tl.arange(0, BLOCK_N)

    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)
    m_i = tl.full([1], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)

    n_start = 0
    while n_start < N:
        n_idx = n_start + n_offsets
        n_mask = n_idx < N

        # Load K tile [BLOCK_N, BLOCK_D_HEAD]
        k_ptrs = (
            k_head_ptr
            + n_idx[:, None] * stride_k_n
            + d_q[None, :] * stride_k_d
        )
        k_mask = n_mask[:, None] & q_mask[None, :]
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)
        k = k.to(tl.float32)

        # Compute scores = K * q
        scores = tl.sum(k * q[None, :], axis=1)
        scores = scores * SCALE
        scores = tl.where(n_mask, scores, -float('inf'))

        block_max = tl.max(scores, axis=0)
        new_m = tl.maximum(m_i, block_max)

        scores_shifted = scores - new_m
        scores_exp = tl.exp(scores_shifted)
        block_l = tl.sum(scores_exp, axis=0)

        alpha = tl.exp(m_i - new_m)

        # Load V tile [BLOCK_N, BLOCK_DV]
        v_ptrs = (
            v_head_ptr
            + n_idx[:, None] * stride_v_n
            + d_v[None, :] * stride_v_d
        )
        v_mask = n_mask[:, None] & (d_v[None, :] < Dv)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        v = v.to(tl.float32)

        weighted_v = tl.sum(v * scores_exp[:, None], axis=0)

        acc = acc * alpha + weighted_v
        l_i = l_i * alpha + block_l
        m_i = new_m

        n_start += BLOCK_N

    acc = acc / l_i
    o_mask = d_v < Dv
    tl.store(o_ptr + d_v * stride_o_d, acc.to(tl.float16), mask=o_mask)


def _decoding_attn_reference(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Dq = Q.shape[-1]
    scale = 1.0 / math.sqrt(Dq)
    scores = torch.matmul(Q, K.transpose(-1, -2)) * scale
    attn = torch.softmax(scores, dim=-1)
    out = torch.matmul(attn, V)
    return out.to(Q.dtype)


def _decoding_attn_triton(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv
    assert H == Hk == Hv
    assert Dq == Dk
    assert N == Nv

    # Kernel is specialized for Dq <= 64, Dv <= 64 and last-dim contiguous
    if (
        Dq > 64
        or Dv > 64
        or Q.stride(-1) != 1
        or K.stride(-1) != 1
        or V.stride(-1) != 1
    ):
        return _decoding_attn_reference(Q, K, V)

    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    stride_q_z, stride_q_h, stride_q_m, stride_q_d = Q.stride()
    stride_k_z, stride_k_h, stride_k_n, stride_k_d = K.stride()
    stride_v_z, stride_v_h, stride_v_n, stride_v_d = V.stride()
    stride_o_z, stride_o_h, stride_o_m, stride_o_d = out.stride()

    scale = 1.0 / math.sqrt(Dq)

    grid = (Z * H * M,)

    _decoding_attn_kernel[grid](
        Q, K, V, out,
        stride_q_z, stride_q_h, stride_q_m, stride_q_d,
        stride_k_z, stride_k_h, stride_k_n, stride_k_d,
        stride_v_z, stride_v_h, stride_v_n, stride_v_d,
        stride_o_z, stride_o_h, stride_o_m, stride_o_d,
        Z, H, M, N, Dq, Dv,
        scale,
    )

    return out


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.

    Args:
        Q: (Z, H, M, Dq) float16
        K: (Z, H, N, Dq) float16
        V: (Z, H, N, Dv) float16

    Returns:
        (Z, H, M, Dv) float16
    """
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        return _decoding_attn_reference(Q, K, V)
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        return _decoding_attn_reference(Q, K, V)
    return _decoding_attn_triton(Q, K, V)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
