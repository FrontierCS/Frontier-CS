import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        gdpa_attn_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'num_stages': 2, 'num_warps': 8}),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
):
    start_m = tl.program_id(0)
    pid_zh = tl.program_id(1)

    offs_qm = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d_qk = tl.arange(0, BLOCK_Dq)
    offs_d_v = tl.arange(0, BLOCK_Dv)

    pid_z = pid_zh // H
    pid_h = pid_zh % H

    Q_ptr += pid_z * stride_qz + pid_h * stride_qh
    K_ptr += pid_z * stride_kz + pid_h * stride_kh
    V_ptr += pid_z * stride_vz + pid_h * stride_vh
    GQ_ptr += pid_z * stride_gqz + pid_h * stride_gqh
    GK_ptr += pid_z * stride_gkz + pid_h * stride_gkh
    O_ptr += pid_z * stride_oz + pid_h * stride_oh

    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    q_ptrs = Q_ptr + (offs_qm[:, None] * stride_qm + offs_d_qk[None, :] * stride_qd)
    gq_ptrs = GQ_ptr + (offs_qm[:, None] * stride_gqm + offs_d_qk[None, :] * stride_gqd)
    
    mask_qm = offs_qm[:, None] < M
    q = tl.load(q_ptrs, mask=mask_qm, other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_qm, other=0.0)

    q_gated = q * tl.sigmoid(gq.to(tl.float32))
    scale = Dq**-0.5
    q_scaled = (q_gated * scale).to(q.dtype)

    for start_n in range(0, N, BLOCK_N):
        offs_kn = start_n + offs_n
        mask_kn = offs_kn < N

        k_ptrs = K_ptr + (offs_kn[None, :] * stride_kn + offs_d_qk[:, None] * stride_kd)
        gk_ptrs = GK_ptr + (offs_kn[None, :] * stride_gkn + offs_d_qk[:, None] * stride_gkd)
        
        k = tl.load(k_ptrs, mask=mask_kn[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_kn[None, :], other=0.0)
        
        k_gated = k * tl.sigmoid(gk.to(tl.float32))

        s = tl.dot(q_scaled, k_gated, allow_tf32=True)
        s += tl.where(mask_kn[None, :], 0, -float('inf'))

        m_ij = tl.max(s, 1)
        p = tl.exp(s - m_ij[:, None])
        l_ij = tl.sum(p, 1)

        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_new = alpha * l_i + beta * l_ij
        
        acc_scaled = acc * (alpha / l_new)[:, None]
        
        p_scaled = p * (beta / l_new)[:, None]
        
        v_ptrs = V_ptr + (offs_kn[:, None] * stride_vn + offs_d_v[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_kn[:, None], other=0.0)
        
        p_typed = p_scaled.to(v.dtype)
        acc = acc_scaled + tl.dot(p_typed, v, allow_tf32=True)

        l_i = l_new
        m_i = m_new

    o_ptrs = O_ptr + (offs_qm[:, None] * stride_om + offs_d_v[None, :] * stride_od)
    tl.store(o_ptrs, acc.to(O_ptr.dtype.element_ty), mask=mask_qm)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), Z * H)
    
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
        BLOCK_Dq=Dq, BLOCK_Dv=Dv
    )

    return O
"""
        return {"code": gdpa_attn_code}
