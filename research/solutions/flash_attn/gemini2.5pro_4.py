import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        flash_attn_code = """
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
    ],
    key=['M', 'N', 'D_HEAD_Q', 'D_HEAD_V', 'causal'],
)
@triton.jit
def _flash_attn_forward_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N, M,
    D_HEAD_Q: tl.constexpr,
    D_HEAD_V: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    causal: tl.constexpr,
):
    start_m = tl.program_id(0)
    b_h = tl.program_id(1)

    b = b_h // H
    h = b_h % H

    q_offset = b * stride_qz + h * stride_qh
    k_offset = b * stride_kz + h * stride_kh
    v_offset = b * stride_vz + h * stride_vh
    o_offset = b * stride_oz + h * stride_oh

    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = O + o_offset

    acc = tl.zeros([BLOCK_M, D_HEAD_V], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, D_HEAD_Q)

    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_dq[None, :]
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)

    sm_scale = 1.0 / (D_HEAD_Q ** 0.5)

    # Loop over K, V blocks
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        start_n_offset = start_n * BLOCK_N
        offs_n = start_n_offset + tl.arange(0, BLOCK_N)

        # Load K
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_dq[None, :]
        mask_n = offs_n < N
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)

        # Compute S = Q @ K.T
        s = tl.dot(q, tl.trans(k))
        s *= sm_scale

        if causal:
            causal_mask = offs_m[:, None] >= offs_n[None, :]
            s = tl.where(causal_mask, s, -float("inf"))

        # Online softmax update
        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(s - m_new[:, None])
        
        alpha = tl.exp(m_i - m_new)
        
        l_i_scaled = l_i * alpha
        l_ij = tl.sum(p, axis=1)
        l_new = l_i_scaled + l_ij

        acc_scaled = acc * alpha[:, None]

        # Load V
        offs_dv = tl.arange(0, D_HEAD_V)
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :]
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        # Update accumulator
        p = p.to(v.dtype)
        acc_update = tl.dot(p, v)
        acc = acc_scaled + acc_update
        
        # Update statistics for next iteration
        l_i = l_new
        m_i = m_new

    # Finalize and store to output
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]

    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :]
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D_HEAD_Q = Q.shape
    _, _, N, D_HEAD_K = K.shape
    _, _, _, D_HEAD_V = V.shape
    
    assert D_HEAD_Q == D_HEAD_K, "Query and Key head dimensions must be equal"
    
    O = torch.empty((Z, H, M, D_HEAD_V), device=Q.device, dtype=Q.dtype)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)

    _flash_attn_forward_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N, M,
        D_HEAD_Q=D_HEAD_Q,
        D_HEAD_V=D_HEAD_V,
        causal=causal,
    )
    return O
"""
        return {"code": flash_attn_code}