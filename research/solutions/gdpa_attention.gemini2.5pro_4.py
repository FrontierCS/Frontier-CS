import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_kernel(
    Q, K, V, GQ, GK, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_batch_head = tl.program_id(0)
    pid_m = tl.program_id(1)

    pid_z = pid_batch_head // H
    pid_h = pid_batch_head % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d_q = tl.arange(0, Dq)
    offs_d_v = tl.arange(0, Dv)

    Q_ptr = Q + pid_z * stride_qz + pid_h * stride_qh
    K_ptr = K + pid_z * stride_kz + pid_h * stride_kh
    V_ptr = V + pid_z * stride_vz + pid_h * stride_vh
    GQ_ptr = GQ + pid_z * stride_gqz + pid_h * stride_gqh
    GK_ptr = GK + pid_z * stride_gkz + pid_h * stride_gkh
    O_ptr = O + pid_z * stride_oz + pid_h * stride_oh

    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    mask_m = offs_m < M
    q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qd)
    gq_ptrs = GQ_ptr + (offs_m[:, None] * stride_gqm + offs_d_q[None, :] * stride_gqd)
    
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)

    qg = q * tl.sigmoid(gq.to(tl.float32)).to(q.dtype)

    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        offs_n_base = start_n * BLOCK_N
        offs_n = offs_n_base + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = K_ptr + (offs_d_q[:, None] * stride_kd + offs_n[None, :] * stride_kn)
        gk_ptrs = GK_ptr + (offs_d_q[:, None] * stride_gkd + offs_n[None, :] * stride_gkn)

        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[None, :], other=0.0)

        kg = k * tl.sigmoid(gk.to(tl.float32)).to(k.dtype)

        s = tl.dot(qg, kg) * scale
        s = tl.where(mask_n[None, :], s, -float('inf'))

        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(s - m_new[:, None])
        
        l_i_new = alpha * l_i + tl.sum(beta, axis=1)

        v_ptrs = V_ptr + (offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        acc = acc * alpha[:, None]
        acc += tl.dot(beta.to(v.dtype), v)

        l_i = l_i_new
        m_i = m_new

    o = acc / l_i[:, None]

    o_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od)
    tl.store(o_ptrs, o.to(O.dtype.element_ty), mask=mask_m[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    scale = 1.0 / math.sqrt(Dq)

    grid = lambda META: (Z * H, triton.cdiv(M, META['BLOCK_M']))

    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq, Dv,
        scale,
    )
    return O
"""
        return {"code": code}