import math
import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import math
import torch
import triton
import triton.language as tl

@triton.jit
def _flash_attn_kernel(
    Q, K, V, Output,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, D,
    sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    m_start = pid_m * BLOCK_M

    offs_d = tl.arange(0, BLOCK_D)
    offs_m = m_start + tl.arange(0, BLOCK_M)

    # Load Q block
    q_offset = pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load_block(Q + q_offset, (BLOCK_M, BLOCK_D)).to(tl.float32)

    # Initialize o, m, l
    o = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)
    m = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # Number of key blocks
    num_k_blocks = (N + BLOCK_N - 1) // BLOCK_N

    blk_n = 0
    while blk_n < num_k_blocks:
        start_n = blk_n * BLOCK_N
        offs_n = start_n + tl.arange(0, BLOCK_N)

        # Load K block
        k_offset = pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load_block(K + k_offset, (BLOCK_N, BLOCK_D)).to(tl.float32)

        # Load V block
        v_offset = pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        v = tl.load_block(V + v_offset, (BLOCK_N, BLOCK_D)).to(tl.float32)

        # Compute S = (Q @ K^T) * sm_scale
        s = tl.dot(q, tl.trans(k)) * sm_scale

        # Mask out-of-bounds
        n_mask = offs_n < N
        s = tl.where(n_mask[None, :], s, float("-inf"))

        # Causal mask
        if causal:
            row_idx = m_start + tl.arange(0, BLOCK_M)[:, None]
            col_idx = start_n + tl.arange(0, BLOCK_N)[None, :]
            causal_mask = col_idx > row_idx
            s = tl.where(causal_mask, float("-inf"), s)

        # Online softmax
        m_new = tl.maximum(m[:, None], tl.max(s, 1))
        exp_scale = tl.exp(m - m_new)
        p = tl.exp(s - m_new[:, None])
        sum_p = tl.sum(p, 1)
        l_new = exp_scale * l + sum_p

        # Update o
        o_partial = tl.dot(p, v)
        o = o * (l * exp_scale)[:, None] / l_new[:, None] + o_partial / l_new[:, None]

        # Update stats
        l = l_new
        m = m_new

        blk_n += 1

    # Store output
    o_offset = pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    tl.store_block(Output + o_offset, o.to(tl.float16))

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    assert K.shape[-1] == D
    assert V.shape[-1] == D
    assert V.shape[0] == Z and V.shape[1] == H and V.shape[2] == N

    sm_scale = 1.0 / math.sqrt(D)
    output = torch.empty_like(Q)

    q_strides = Q.stride()
    k_strides = K.stride()
    v_strides = V.stride()
    o_strides = output.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = D

    grid = (Z, H, (M + BLOCK_M - 1) // BLOCK_M)

    _flash_attn_kernel[grid](
        Q, K, V, output,
        q_strides[0], q_strides[1], q_strides[2], q_strides[3],
        k_strides[0], k_strides[1], k_strides[2], k_strides[3],
        v_strides[0], v_strides[1], v_strides[2], v_strides[3],
        o_strides[0], o_strides[1], o_strides[2], o_strides[3],
        Z, H, M, N, D,
        sm_scale,
        causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D
    )

    return output
"""
        return {"code": code}
