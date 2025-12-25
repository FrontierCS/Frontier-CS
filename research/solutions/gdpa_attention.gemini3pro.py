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
import math

@triton.jit
def _gdpa_fwd_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_ok,
    Z, H, M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, 
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
    sm_scale: tl.constexpr
):
    pid_m = tl.program_id(0)
    off_z = tl.program_id(1)
    off_h = tl.program_id(2)

    # Base pointers for this batch/head
    Q_ptr_base = Q + off_z * stride_qz + off_h * stride_qh
    K_ptr_base = K + off_z * stride_kz + off_h * stride_kh
    V_ptr_base = V + off_z * stride_vz + off_h * stride_vh
    GQ_ptr_base = GQ + off_z * stride_qz + off_h * stride_qh
    GK_ptr_base = GK + off_z * stride_kz + off_h * stride_kh
    Out_ptr_base = Out + off_z * stride_oz + off_h * stride_oh

    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dv = tl.arange(0, BLOCK_DV)
    offs_n_base = tl.arange(0, BLOCK_N)

    # Q / GQ Pointers
    Q_ptrs = Q_ptr_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk
    GQ_ptrs = GQ_ptr_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk

    # Mask for Q loading (handle M not multiple of BLOCK_M)
    mask_m = offs_m[:, None] < M
    
    # Load Q, GQ
    # We assume Dq/Dv dimensions are consistent with block sizes (or padded by next_power_of_2 logic)
    q = tl.load(Q_ptrs, mask=mask_m, other=0.0)
    gq = tl.load(GQ_ptrs, mask=mask_m, other=0.0)
    
    # Apply gating to Q
    # Qg = Q * sigmoid(GQ)
    q_g = q * tl.sigmoid(gq)
    # Apply scaling factor
    q_g = (q_g * sm_scale).to(q_g.dtype)

    # Initialize accumulators for streaming softmax
    # m_i: max score so far
    # l_i: sum of exponentials so far
    # acc: accumulated output
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # Loop over K, V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_n_base
        mask_n = offs_n[None, :] < N
        
        # Load K, GK
        # Transpose is handled implicitly during dot or via pointer math
        # Here we load K normally (N, D) -> (BLOCK_N, BLOCK_DQ)
        K_ptrs = K_ptr_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kk
        GK_ptrs = GK_ptr_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kk
        
        k = tl.load(K_ptrs, mask=mask_n, other=0.0)
        gk = tl.load(GK_ptrs, mask=mask_n, other=0.0)
        
        # Apply gating to K
        # Kg = K * sigmoid(GK)
        k_g = k * tl.sigmoid(gk)
        
        # Dot Product: Q_g (M, D) x K_g^T (D, N) -> (M, N)
        # q_g is (BLOCK_M, BLOCK_DQ), k_g is (BLOCK_N, BLOCK_DQ)
        qk = tl.dot(q_g, tl.trans(k_g))
        
        # Mask out-of-bounds attention scores (for N dimension)
        if start_n + BLOCK_N > N:
             qk = tl.where(offs_n[None, :] < N, qk, float("-inf"))
        
        # Streaming Softmax Computation
        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        
        # Exponentials
        p = tl.exp(qk - m_new[:, None])
        
        # Correction factor for existing accumulators
        alpha = tl.exp(m_i - m_new)
        
        # Load V
        V_ptrs = V_ptr_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vk
        v = tl.load(V_ptrs, mask=mask_n, other=0.0)
        
        # Accumulate Output
        # acc = acc * alpha + P * V
        # Cast p to matching dtype for efficient dot product
        acc = acc * alpha[:, None] + tl.dot(p.to(v.dtype), v)
        
        # Update normalization sum
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # Update running max
        m_i = m_new

    # Final Normalization
    acc = acc / l_i[:, None]
    
    # Store Output
    Out_ptrs = Out_ptr_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ok
    tl.store(Out_ptrs, acc.to(Out.dtype.element_ty), mask=mask_m)

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Block sizes
    # 128x64 is a standard efficient tiling for FP16 attention
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DQ = triton.next_power_of_2(Dq)
    BLOCK_DV = triton.next_power_of_2(Dv)
    
    # Kernel config
    num_warps = 4
    num_stages = 3
    
    grid = (triton.cdiv(M, BLOCK_M), Z, H)
    sm_scale = 1.0 / (Dq ** 0.5)
    
    _gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DQ=BLOCK_DQ, BLOCK_DV=BLOCK_DV,
        sm_scale=sm_scale,
        num_warps=num_warps, num_stages=num_stages
    )
    
    return Out
"""
        }
