import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'DQK', 'DV'],
)
@triton.jit
def _gdpa_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_gqz, stride_gqh, stride_gqm, stride_gqk,
    stride_gkz, stride_gkh, stride_gkn, stride_gkk,
    stride_oz, stride_oh, stride_om, stride_ov,
    sm_scale,
    Z, H, M, N, 
    DQK, DV,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, 
    BLOCK_DQK: tl.constexpr, BLOCK_DV: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    i_z = off_hz // H
    i_h = off_hz % H

    q_offset = i_z * stride_qz + i_h * stride_qh
    k_offset = i_z * stride_kz + i_h * stride_kh
    v_offset = i_z * stride_vz + i_h * stride_vh
    gq_offset = i_z * stride_gqz + i_h * stride_gqh
    gk_offset = i_z * stride_gkz + i_h * stride_gkh
    o_offset = i_z * stride_oz + i_h * stride_oh

    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dqk = tl.arange(0, BLOCK_DQK)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_dqk = offs_dqk < DQK
    mask_dv = offs_dv < DV

    Q_ptrs = Q + q_offset + offs_m[:, None] * stride_qm + offs_dqk[None, :] * stride_qk
    GQ_ptrs = GQ + gq_offset + offs_m[:, None] * stride_gqm + offs_dqk[None, :] * stride_gqk

    # Load Q and GQ
    q = tl.load(Q_ptrs, mask=mask_m[:, None] & mask_dqk[None, :], other=0.0)
    gq = tl.load(GQ_ptrs, mask=mask_m[:, None] & mask_dqk[None, :], other=0.0)

    # Apply gating to Q: Qg = Q * sigmoid(GQ)
    q = q * tl.sigmoid(gq)
    # Apply scale
    q = q * sm_scale

    # Initialize stats
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    K_base = K + k_offset
    GK_base = GK + gk_offset
    V_base = V + v_offset

    offs_n = tl.arange(0, BLOCK_N)
    
    for start_n in range(0, N, BLOCK_N):
        cols = start_n + offs_n
        mask_n = cols < N
        
        # Load K, GK
        # Transposed access: K is loaded as (BLOCK_N, DQK) to perform dot(Q, K.T)
        K_ptrs = K_base + cols[:, None] * stride_kn + offs_dqk[None, :] * stride_kk
        GK_ptrs = GK_base + cols[:, None] * stride_gkn + offs_dqk[None, :] * stride_gkk
        
        k = tl.load(K_ptrs, mask=mask_n[:, None] & mask_dqk[None, :], other=0.0)
        gk = tl.load(GK_ptrs, mask=mask_n[:, None] & mask_dqk[None, :], other=0.0)
        
        # Apply gating to K: Kg = K * sigmoid(GK)
        k = k * tl.sigmoid(gk)
        
        # Compute Q K^T
        qk = tl.dot(q, tl.trans(k))
        
        # Mask padded elements
        qk = tl.where(mask_n[None, :], qk, float("-inf"))
        
        # Online Softmax
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_new = l_i * alpha + l_ij * beta
        
        # Load V
        V_ptrs = V_base + cols[:, None] * stride_vn + offs_dv[None, :] * stride_vk
        v = tl.load(V_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)
        
        # Accumulate Output
        p_w = p * beta[:, None]
        acc = acc * alpha[:, None]
        # Cast to fp16 for accumulation if necessary, but keep acc in fp32
        acc = tl.dot(p_w.to(tl.float16), v, acc)
        
        l_i = l_new
        m_i = m_new

    # Finalize
    acc = acc / l_i[:, None]
    
    # Store
    O_ptrs = Out + o_offset + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ov
    tl.store(O_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    BLOCK_DQK = triton.next_power_of_2(Dq)
    BLOCK_DV = triton.next_power_of_2(Dv)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    sm_scale = 1.0 / (Dq ** 0.5)
    
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        sm_scale,
        Z, H, M, N,
        Dq, Dv,
        BLOCK_DQK=BLOCK_DQK, BLOCK_DV=BLOCK_DV
    )
    
    return Out
"""
        }
