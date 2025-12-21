import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=1, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    start_m = pid_m * BLOCK_M
    if start_m >= M:
        return

    q_base = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + start_m * stride_qm
    m_offsets = tl.arange(0, BLOCK_M)
    m_mask = start_m + m_offsets < M
    d_offsets = tl.arange(0, Dq)
    q = tl.load(
        q_base + m_offsets[:, None] * stride_qm + d_offsets[None, :] * stride_qd,
        mask=m_mask[:, None] & (d_offsets[None, :] < Dq),
        other=0.0,
    )
    q = q.to(tl.float32)

    m_i = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    dv_offsets = tl.arange(0, Dv)
    o_i = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)

    n_offsets = tl.arange(0, BLOCK_N)
    start_n = 0
    while start_n < N:
        n_mask = start_n + n_offsets < N
        if tl.sum(tl.where(n_mask, 1, 0).to(tl.float32)) == 0:
            break

        k_base = K_ptr + pid_z * stride_kz + pid_h * stride_kh + start_n * stride_kn
        k = tl.load(
            k_base + n_offsets[:, None] * stride_kn + d_offsets[None, :] * stride_kd,
            mask=n_mask[:, None] & (d_offsets[None, :] < Dq),
            other=0.0,
        )
        k = k.to(tl.float32)

        v_base = V_ptr + pid_z * stride_vz + pid_h * stride_vh + start_n * stride_vn
        v = tl.load(
            v_base + n_offsets[:, None] * stride_vn + dv_offsets[None, :] * stride_vd,
            mask=n_mask[:, None] & (dv_offsets[None, :] < Dv),
            other=0.0,
        )
        v = v.to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * sm_scale

        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        o_ij = tl.dot(p, v)

        new_m = tl.maximum(m_i, m_ij)
        e_old = tl.exp(m_i - new_m[:, None])
        e_new = tl.exp(m_ij - new_m[:, None])
        o_i = o_i * e_old + o_ij * e_new
        l_i = l_i * tl.squeeze(e_old, 1) + l_ij * tl.squeeze(e_new, 1)
        m_i = new_m

        start_n += BLOCK_N

    o_i = o_i / l_i[:, None]

    o_base = O_ptr + pid_z * stride_oz + pid_h * stride_oh + start_m * stride_om
    o = o_i.to(O_ptr.dtype.element_ty)
    tl.store(
        o_base + m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_od,
        o,
        mask=m_mask[:, None] & (dv_offsets[None, :] < Dv),
    )

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    assert K.shape[:2] == (Z, H) and K.shape[3] == Dq
    N = K.shape[2]
    assert V.shape[:2] == (Z, H) and V.shape[2] == N
    Dv = V.shape[3]
    if M == 0 or N == 0:
        return torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    sm_scale = 1.0 / math.sqrt(Dq)
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    stride_q = Q.stride()
    stride_k = K.stride()
    stride_v = V.stride()
    stride_o = O.stride()
    num_blocks_m = triton.cdiv(M, 64)
    grid = (Z, H, num_blocks_m)
    attn_kernel[grid](
        Q, K, V, O,
        M, N, Dq, Dv,
        stride_q[0], stride_q[1], stride_q[2], stride_q[3],
        stride_k[0], stride_k[1], stride_k[2], stride_k[3],
        stride_v[0], stride_v[1], stride_v[2], stride_v[3],
        stride_o[0], stride_o[1], stride_o[2], stride_o[3],
        sm_scale=sm_scale,
    )
    return O
"""
        return {"code": code}
