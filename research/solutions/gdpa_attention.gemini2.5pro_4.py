import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic balanced configs
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 4}),
        
        # Configs with more stages for latency hiding
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 4, 'num_warps': 4}),

        # Configs with more warps for higher occupancy/parallelism
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 8}),

        # Larger block sizes for sequence reuse
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 8}),

    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_forward_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
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
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    pid_m_block = tl.program_id(axis=1)
    
    pid_z = pid // H
    pid_h = pid % H

    q_base_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
    k_base_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    v_base_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    gq_base_ptr = GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh
    gk_base_ptr = GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh
    o_base_ptr = O_ptr + pid_z * stride_oz + pid_h * stride_oh

    offs_m = pid_m_block * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    mask_m = offs_m < M
    
    q_ptrs = q_base_ptr + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = gq_base_ptr + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd

    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)

    gq_sigmoid = tl.sigmoid(gq.to(tl.float32)).to(tl.float16)
    q_gated = q * gq_sigmoid

    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    offs_dv = tl.arange(0, BLOCK_DV)
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = k_base_ptr + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        gk_ptrs = gk_base_ptr + offs_n[:, None] * stride_gkn + offs_dq[None, :] * stride_kd
        v_ptrs = v_base_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        gk_sigmoid = tl.sigmoid(gk.to(tl.float32)).to(tl.float16)
        k_gated = k * gk_sigmoid

        s = tl.dot(q_gated, k_gated.T, out_dtype=tl.float32)
        s *= scale
        s = tl.where(mask_m[:, None] & mask_n[None, :], s, -float('inf'))

        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        p = tl.exp(s - m_new[:, None])
        
        alpha = tl.exp(m_i - m_new)
        acc *= alpha[:, None]
        
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        acc += tl.dot(p.to(tl.float16), v, out_dtype=tl.float32)
        m_i = m_new

    o = acc / l_i[:, None]
    
    o_ptrs = o_base_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = Dq**-0.5
    
    grid = lambda META: (Z * H, triton.cdiv(M, META['BLOCK_M']))
    
    _gdpa_attn_forward_kernel[grid](
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
        BLOCK_DQ=Dq,
        BLOCK_DV=Dv,
    )
    return O
"""
        return {"code": code}
