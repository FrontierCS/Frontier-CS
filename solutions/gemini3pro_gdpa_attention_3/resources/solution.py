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

@triton.jit
def _gdpa_fwd_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_gqz, stride_gqh, stride_gqm, stride_gqk,
    stride_gkz, stride_gkh, stride_gkn, stride_gkk,
    stride_oz, stride_oh, stride_om, stride_on,
    sm_scale,
    Z, H, M, N, D_Q, D_V,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    # -----------------------------------------------------------
    # Q and GQ Loading
    # -----------------------------------------------------------
    # Offsets for Q/GQ: [BLOCK_M, BLOCK_DQ]
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    
    # Check bounds
    mask_m = offs_m < M
    mask_dq = offs_dq < D_Q
    mask_q = mask_m[:, None] & mask_dq[None, :]
    
    # Pointers
    q_ptrs = Q + (off_z * stride_qz + off_h * stride_qh) + \
             (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk)
    gq_ptrs = GQ + (off_z * stride_gqz + off_h * stride_gqh) + \
              (offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqk)
              
    # Load and Gate
    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    
    q = q * tl.sigmoid(gq)
    q = q * sm_scale
    q = q.to(tl.float16)

    # -----------------------------------------------------------
    # Accumulators
    # -----------------------------------------------------------
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # -----------------------------------------------------------
    # K/V Base Pointers & Offsets
    # -----------------------------------------------------------
    k_base = K + (off_z * stride_kz + off_h * stride_kh)
    gk_base = GK + (off_z * stride_gkz + off_h * stride_gkh)
    v_base = V + (off_z * stride_vz + off_h * stride_vh)
    
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)
    mask_dv = offs_dv < D_V
    
    # -----------------------------------------------------------
    # Loop over N
    # -----------------------------------------------------------
    for start_n in range(0, N, BLOCK_N):
        cols = start_n + offs_n
        mask_n = cols < N
        
        # --- Load K, GK ---
        # Shape: [BLOCK_N, BLOCK_DQ]
        mask_k = mask_n[:, None] & mask_dq[None, :]
        
        k_ptrs = k_base + (cols[:, None] * stride_kn + offs_dq[None, :] * stride_kk)
        gk_ptrs = gk_base + (cols[:, None] * stride_gkn + offs_dq[None, :] * stride_gkk)
        
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_k, other=0.0)
        
        # Gate K
        k = k * tl.sigmoid(gk)
        k = k.to(tl.float16)
        
        # --- Attention Score ---
        # q: [M, D], k: [N, D] -> qk: [M, N]
        # We compute q @ k.T
        qk = tl.dot(q, tl.trans(k))
        
        # Mask padded parts of N
        qk = tl.where(mask_n[None, :], qk, float("-inf"))
        
        # --- Softmax Stats ---
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        # --- Update Global Stats ---
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_i = l_i * alpha + l_ij * beta
        
        # --- Load V ---
        # Shape: [BLOCK_N, BLOCK_DV]
        mask_v = mask_n[:, None] & mask_dv[None, :]
        v_ptrs = v_base + (cols[:, None] * stride_vn + offs_dv[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # --- Update Accumulator ---
        p = p.to(tl.float16)
        # p: [M, N], v: [N, DV] -> pv: [M, DV]
        pv = tl.dot(p, v)
        acc = acc * alpha[:, None] + pv * beta[:, None]
        
        m_i = m_new

    # -----------------------------------------------------------
    # Store Output
    # -----------------------------------------------------------
    out = acc / l_i[:, None]
    out = out.to(tl.float16)
    
    out_ptrs = Out + (off_z * stride_oz + off_h * stride_oh) + \
               (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_on)
    
    mask_out = mask_m[:, None] & mask_dv[None, :]
    tl.store(out_ptrs, out, mask=mask_out)

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DQ = triton.next_power_of_2(Dq)
    BLOCK_DV = triton.next_power_of_2(Dv)
    
    num_warps = 4 if Dq <= 64 else 8
    num_stages = 3
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        sm_scale=1.0 / (Dq ** 0.5),
        Z=Z, H=H, M=M, N=N, D_Q=Dq, D_V=Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DQ=BLOCK_DQ, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps, num_stages=num_stages
    )
    
    return Out
"""
        }
