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
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32}, num_warps=4, num_stages=2),
    ],
    key=['N_CTX', 'D_HEAD'],
)
@triton.jit
def _gdpa_kernel(
    Q, K, V, GQ, GK, Out,
    stride_z_q, stride_h_q, stride_m_q, stride_d_q,
    stride_z_k, stride_h_k, stride_n_k, stride_d_k,
    stride_z_v, stride_h_v, stride_n_v, stride_d_v,
    stride_z_gq, stride_h_gq, stride_m_gq, stride_d_gq,
    stride_z_gk, stride_h_gk, stride_n_gk, stride_d_gk,
    stride_z_o, stride_h_o, stride_m_o, stride_d_o,
    Z, H, N_CTX, D_HEAD,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    tl_m = tl.program_id(0)
    tl_zh = tl.program_id(1)
    tl_h = tl_zh % H
    tl_z = tl_zh // H

    # Offsets
    off_q = tl_z * stride_z_q + tl_h * stride_h_q
    off_k = tl_z * stride_z_k + tl_h * stride_h_k
    off_v = tl_z * stride_z_v + tl_h * stride_h_v
    off_gq = tl_z * stride_z_gq + tl_h * stride_h_gq
    off_gk = tl_z * stride_z_gk + tl_h * stride_h_gk
    off_o = tl_z * stride_z_o + tl_h * stride_h_o

    # Block Pointers
    # Q, GQ: (M, D) - Row Major
    Q_ptr = tl.make_block_ptr(
        base=Q + off_q,
        shape=(N_CTX, D_HEAD),
        strides=(stride_m_q, stride_d_q),
        offsets=(tl_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, D_HEAD),
        order=(1, 0)
    )
    GQ_ptr = tl.make_block_ptr(
        base=GQ + off_gq,
        shape=(N_CTX, D_HEAD),
        strides=(stride_m_gq, stride_d_gq),
        offsets=(tl_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, D_HEAD),
        order=(1, 0)
    )
    
    # K, GK: (D, N) - Column Major (transposed load for dot product)
    K_ptr = tl.make_block_ptr(
        base=K + off_k,
        shape=(D_HEAD, N_CTX),
        strides=(stride_d_k, stride_n_k),
        offsets=(0, 0),
        block_shape=(D_HEAD, BLOCK_N),
        order=(0, 1)
    )
    GK_ptr = tl.make_block_ptr(
        base=GK + off_gk,
        shape=(D_HEAD, N_CTX),
        strides=(stride_d_gk, stride_n_gk),
        offsets=(0, 0),
        block_shape=(D_HEAD, BLOCK_N),
        order=(0, 1)
    )

    # V: (N, D) - Row Major
    V_ptr = tl.make_block_ptr(
        base=V + off_v,
        shape=(N_CTX, D_HEAD),
        strides=(stride_n_v, stride_d_v),
        offsets=(0, 0),
        block_shape=(BLOCK_N, D_HEAD),
        order=(1, 0)
    )

    # Output
    O_ptr = tl.make_block_ptr(
        base=Out + off_o,
        shape=(N_CTX, D_HEAD),
        strides=(stride_m_o, stride_d_o),
        offsets=(tl_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, D_HEAD),
        order=(1, 0)
    )

    # Load Q, GQ
    # boundary_check=(0,1) handles cases where sizes are not multiples of block
    q = tl.load(Q_ptr, boundary_check=(0,1))
    gq = tl.load(GQ_ptr, boundary_check=(0,1))
    
    # Gate Q
    q = q * tl.sigmoid(gq)
    q = (q * sm_scale).to(tl.float16)

    # Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, D_HEAD], dtype=tl.float32)

    # Loop over K, V (N dimension)
    for start_n in range(0, N_CTX, BLOCK_N):
        # Load K, GK
        k = tl.load(K_ptr, boundary_check=(0,1))
        gk = tl.load(GK_ptr, boundary_check=(0,1))
        
        # Load V
        v = tl.load(V_ptr, boundary_check=(0,1))

        # Gate K
        k = k * tl.sigmoid(gk)
        
        # Compute Attention Scores: Q (M, D) @ K (D, N) -> (M, N)
        qk = tl.dot(q, k)
        
        # Mask out-of-bounds columns if necessary
        if start_n + BLOCK_N > N_CTX:
            offs_n = start_n + tl.arange(0, BLOCK_N)
            mask_n = offs_n[None, :] < N_CTX
            qk = tl.where(mask_n, qk, float('-inf'))
        
        # Softmax stats
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)

        # Update stats
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)

        l_i = l_i * alpha + l_ij * beta
        
        # Update accumulator: acc (M, D) + P (M, N) @ V (N, D)
        p = p.to(tl.float16)
        pv = tl.dot(p, v)
        acc = acc * alpha[:, None] + pv * beta[:, None]
        m_i = m_new

        # Advance pointers
        K_ptr = tl.advance(K_ptr, (0, BLOCK_N))
        GK_ptr = tl.advance(GK_ptr, (0, BLOCK_N))
        V_ptr = tl.advance(V_ptr, (BLOCK_N, 0))

    # Finalize
    acc = acc / l_i[:, None]
    tl.store(O_ptr, acc.to(tl.float16), boundary_check=(0,1))

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    
    sm_scale = 1.0 / math.sqrt(Dq)
    Out = torch.empty_like(Q)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, Dq,
        sm_scale
    )
    
    return Out
"""
        }