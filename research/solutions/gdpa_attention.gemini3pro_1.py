import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'HEAD_DIM_Q', 'HEAD_DIM_V']
)
@triton.jit
def _gdpa_attn_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    stride_gqz, stride_gqh, stride_gqm, stride_gqk,
    stride_gkz, stride_gkh, stride_gkn, stride_gkk,
    Z, H, M, N,
    HEAD_DIM_Q: tl.constexpr, HEAD_DIM_V: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    # Q offsets
    q_offset = off_z * stride_qz + off_h * stride_qh
    gq_offset = off_z * stride_gqz + off_h * stride_gqh
    
    # K/V/GK offsets
    k_offset = off_z * stride_kz + off_h * stride_kh
    gk_offset = off_z * stride_gkz + off_h * stride_gkh
    v_offset = off_z * stride_vz + off_h * stride_vh
    
    # Out offsets
    o_offset = off_z * stride_oz + off_h * stride_oh
    
    # Load Q, GQ using Block Pointers
    # Q shape (M, Dq)
    Q_ptr = tl.make_block_ptr(
        base=Q + q_offset,
        shape=(M, HEAD_DIM_Q),
        strides=(stride_qm, stride_qk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM_Q),
        order=(1, 0)
    )
    GQ_ptr = tl.make_block_ptr(
        base=GQ + gq_offset,
        shape=(M, HEAD_DIM_Q),
        strides=(stride_gqm, stride_gqk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM_Q),
        order=(1, 0)
    )
    
    q = tl.load(Q_ptr, boundary_check=(0,), padding_option="zero")
    gq = tl.load(GQ_ptr, boundary_check=(0,), padding_option="zero")
    
    # Gated Q Computation
    # Qg = Q * sigmoid(GQ)
    sm_scale = 1.0 / tl.sqrt(tl.cast(HEAD_DIM_Q, tl.float32))
    q_g = q * tl.sigmoid(gq)
    q_g = (q_g * sm_scale).to(tl.float16)
    
    # Accumulators for Streaming Softmax
    acc = tl.zeros([BLOCK_M, HEAD_DIM_V], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    
    # K Block Pointer (Transposed View for Dot Product)
    # Physical shape (N, Dq), we view as (Dq, N)
    # Strides swapped: (stride_kk, stride_kn)
    K_ptr = tl.make_block_ptr(
        base=K + k_offset,
        shape=(HEAD_DIM_Q, N),
        strides=(stride_kk, stride_kn),
        offsets=(0, 0),
        block_shape=(HEAD_DIM_Q, BLOCK_N),
        order=(0, 1)
    )
    
    # GK Block Pointer (Transposed View)
    GK_ptr = tl.make_block_ptr(
        base=GK + gk_offset,
        shape=(HEAD_DIM_Q, N),
        strides=(stride_gkk, stride_gkn),
        offsets=(0, 0),
        block_shape=(HEAD_DIM_Q, BLOCK_N),
        order=(0, 1)
    )
    
    # V Block Pointer
    V_ptr = tl.make_block_ptr(
        base=V + v_offset,
        shape=(N, HEAD_DIM_V),
        strides=(stride_vn, stride_vk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, HEAD_DIM_V),
        order=(1, 0)
    )
    
    # Loop over K/V blocks
    for start_n in range(0, N, BLOCK_N):
        # Load K, GK
        k = tl.load(K_ptr, boundary_check=(1,), padding_option="zero")
        gk = tl.load(GK_ptr, boundary_check=(1,), padding_option="zero")
        
        # Gated K Computation
        # Kg = K * sigmoid(GK)
        k_g = k * tl.sigmoid(gk)
        k_g = k_g.to(tl.float16)
        
        # Compute Attention Scores
        # Q (M, D) @ K (D, N) -> (M, N)
        qk = tl.dot(q_g, k_g)
        
        # Online Softmax Update
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(m_ij - m_i_new)
        
        # Update running sum of exps
        l_i = l_i * alpha + l_ij * beta
        
        # Load V
        v = tl.load(V_ptr, boundary_check=(0,), padding_option="zero")
        
        # Accumulate Output
        p = p.to(tl.float16)
        p_beta = p * beta[:, None].to(tl.float16)
        
        pv = tl.dot(p_beta, v)
        acc = acc * alpha[:, None] + pv
        
        # Update max
        m_i = m_i_new
        
        # Advance pointers
        K_ptr = tl.advance(K_ptr, (0, BLOCK_N))
        GK_ptr = tl.advance(GK_ptr, (0, BLOCK_N))
        V_ptr = tl.advance(V_ptr, (BLOCK_N, 0))
        
    # Finalize Output
    acc = acc / l_i[:, None]
    acc = acc.to(tl.float16)
    
    # Store Output
    O_ptr = tl.make_block_ptr(
        base=Out + o_offset,
        shape=(M, HEAD_DIM_V),
        strides=(stride_om, stride_on),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM_V),
        order=(1, 0)
    )
    tl.store(O_ptr, acc, boundary_check=(0,))

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Z, H, M, N,
        HEAD_DIM_Q=Dq, HEAD_DIM_V=Dv
    )
    
    return Out
"""
        }