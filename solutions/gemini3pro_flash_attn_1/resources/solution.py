import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, 
    BLOCK_DK: tl.constexpr, BLOCK_DV: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H

    # Pointers
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh

    # Offsets
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_DK)
    offs_v = tl.arange(0, BLOCK_DV)

    # Q Ptr
    Q_ptr = Q + q_offset + offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qk
    
    # Load Q
    q = tl.load(Q_ptr)
    q = q * sm_scale
    
    # Init accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # K/V Base Ptrs
    K_ptr_base = K + k_offset + offs_k[None, :] * stride_kk
    V_ptr_base = V + v_offset + offs_v[None, :] * stride_vk

    # Loop bounds
    # For causal, we process K blocks up to the one covering start_m
    lo = 0
    hi = (start_m + 1) * BLOCK_M if IS_CAUSAL else N_CTX
    
    for start_n in range(lo, hi, BLOCK_N):
        # Load K
        k_ptr = K_ptr_base + (start_n + offs_n)[:, None] * stride_kn
        k = tl.load(k_ptr)
        
        # QK^T
        qk = tl.dot(q, tl.trans(k))
        
        if IS_CAUSAL:
            # Mask where global_row < global_col
            if start_n + BLOCK_N > start_m * BLOCK_M:
                mask = offs_m[:, None] >= (start_n + offs_n[None, :])
                qk = tl.where(mask, qk, float("-inf"))
        
        # Online Softmax
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        # Update accumulators
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        acc = acc * alpha[:, None]
        
        # Load V
        v_ptr = V_ptr_base + (start_n + offs_n)[:, None] * stride_vn
        v = tl.load(v_ptr)
        
        # P @ V
        p_val = p.to(tl.float16) * beta[:, None].to(tl.float16)
        acc += tl.dot(p_val, v)
        
        l_i = l_i * alpha + l_ij * beta
        m_i = m_new

    # Finalize
    acc = acc / l_i[:, None]
    
    # Store
    O_ptr = Out + o_offset + offs_m[:, None] * stride_om + offs_v[None, :] * stride_on
    tl.store(O_ptr, acc.to(tl.float16))

def flash_attn(Q, K, V, causal=True):
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)
    
    sm_scale = 1.0 / (Dq ** 0.5)
    
    BLOCK_M = 128
    BLOCK_N = 64
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DK=Dq, BLOCK_DV=Dv,
        IS_CAUSAL=causal,
        num_warps=8,
        num_stages=4
    )
    return Out
"""
        return {"code": code}
