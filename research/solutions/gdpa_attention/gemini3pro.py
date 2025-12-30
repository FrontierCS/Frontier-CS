import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code_str = r"""
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
    ],
    key=['M', 'N', 'Dq', 'Dv']
)
@triton.jit
def gdpa_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, 
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)
    
    off_z = pid_zh // H
    off_h = pid_zh % H
    
    # Compute base offsets for this batch/head
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh
    
    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Load Q and GQ
    q_ptrs = Q + q_offset + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk)
    gq_ptrs = GQ + q_offset + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk)
    
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Apply gating: Q_gated = Q * sigmoid(GQ)
    # Apply scaling: Q_scaled = Q_gated * sm_scale
    # Cast to float16 to ensure Tensor Core usage in dot product
    q = (q * tl.sigmoid(gq) * sm_scale).to(tl.float16)
    
    # Initialize accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # Loop over N blocks (Key/Value)
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Load K and GK
        k_ptrs = K + k_offset + (offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kk)
        gk_ptrs = GK + k_offset + (offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kk)
        
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Apply gating: K_gated = K * sigmoid(GK)
        k = (k * tl.sigmoid(gk)).to(tl.float16)
        
        # Compute QK^T
        qk = tl.dot(q, k.T)
        
        # Mask out-of-bounds keys
        if start_n + BLOCK_N > N:
             qk = tl.where(mask_n[None, :], qk, float("-inf"))
        
        # Online Softmax
        m_ij = tl.max(qk, 1)
        m_new = tl.max(m_i, m_ij)
        
        p = tl.exp(qk - m_new[:, None])
        
        # Load V
        v_ptrs = V + v_offset + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Update accumulators
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_new

    # Finalize
    acc = acc / l_i[:, None]
    
    # Store Output
    o_ptrs = Out + o_offset + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_on)
    tl.store(o_ptrs, acc.to(Out.dtype.element_ty), mask=mask_m[:, None])

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    sm_scale = 1.0 / (Dq ** 0.5)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        sm_scale,
        BLOCK_DQ=Dq, BLOCK_DV=Dv
    )
    return Out
"""
        return {"code": code_str}