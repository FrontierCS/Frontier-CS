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
def gdpa_kernel(
    Q, K, V, GQ, GK, Out,
    sqz, sqh, sqm, sqk,
    skz, skh, skn, skk,
    svz, svh, svn, svk,
    sgqz, sgqh, sgqm, sgqk,
    sgkz, sgkh, sgkn, sgkk,
    soz, soh, som, son,
    Z, H, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    HEAD_DIM: tl.constexpr
):
    tl.static_assert(BLOCK_N <= HEAD_DIM)
    start_m = tl.program_id(0)
    off_z = tl.program_id(1) // H
    off_h = tl.program_id(1) % H
    
    # Compute offsets for the current batch and head
    q_off = off_z * sqz + off_h * sqh
    k_off = off_z * skz + off_h * skh
    v_off = off_z * svz + off_h * svh
    gq_off = off_z * sgqz + off_h * sgqh
    gk_off = off_z * sgkz + off_h * sgkh
    o_off = off_z * soz + off_h * soh
    
    # Initialize Block Pointers for Q and GQ
    # Grid computes BLOCK_M rows of Output
    Q_ptr = tl.make_block_ptr(
        base=Q + q_off,
        shape=(N_CTX, HEAD_DIM),
        strides=(sqm, sqk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM),
        order=(1, 0)
    )
    GQ_ptr = tl.make_block_ptr(
        base=GQ + gq_off,
        shape=(N_CTX, HEAD_DIM),
        strides=(sgqm, sgqk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM),
        order=(1, 0)
    )
    
    # Initialize Block Pointers for K, GK, V
    # These will iterate over the sequence length N
    K_ptr = tl.make_block_ptr(
        base=K + k_off,
        shape=(N_CTX, HEAD_DIM),
        strides=(skn, skk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, HEAD_DIM),
        order=(1, 0)
    )
    GK_ptr = tl.make_block_ptr(
        base=GK + gk_off,
        shape=(N_CTX, HEAD_DIM),
        strides=(sgkn, sgkk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, HEAD_DIM),
        order=(1, 0)
    )
    V_ptr = tl.make_block_ptr(
        base=V + v_off,
        shape=(N_CTX, HEAD_DIM),
        strides=(svn, svk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, HEAD_DIM),
        order=(1, 0)
    )
    
    # Initialize Online Softmax Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, HEAD_DIM], dtype=tl.float32)
    
    qk_scale = 1.0 / math.sqrt(HEAD_DIM)
    
    # Load Q and GQ tiles
    q = tl.load(Q_ptr)
    gq = tl.load(GQ_ptr)
    
    # Apply Gating to Q
    # Computation in fp32 for stability, then back to fp16
    q = q.to(tl.float32)
    gq = gq.to(tl.float32)
    q = q * tl.sigmoid(gq) * qk_scale
    q = q.to(tl.float16)
    
    # Loop over K/V blocks
    for start_n in range(0, N_CTX, BLOCK_N):
        # Load K, GK, V
        k = tl.load(K_ptr)
        gk = tl.load(GK_ptr)
        v = tl.load(V_ptr)
        
        # Apply Gating to K
        k = k.to(tl.float32)
        gk = gk.to(tl.float32)
        k = k * tl.sigmoid(gk)
        k = k.to(tl.float16)
        
        # Compute Attention Scores: Q * K^T
        # q: (BLOCK_M, HEAD_DIM), k: (BLOCK_N, HEAD_DIM) -> qk: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        
        # Online Softmax updates
        m_ij = tl.max(qk, 1) # Row max for current block
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        # Combine with previous stats
        m_new = tl.max(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        # Update accumulator
        acc = acc * alpha[:, None]
        p = p.to(tl.float16)
        # p: (BLOCK_M, BLOCK_N), v: (BLOCK_N, HEAD_DIM) -> (BLOCK_M, HEAD_DIM)
        acc = acc + tl.dot(p, v) * beta[:, None]
        
        # Update running max and sum
        l_i = l_i * alpha + l_ij * beta
        m_i = m_new
        
        # Advance pointers to next block
        K_ptr = tl.advance(K_ptr, (BLOCK_N, 0))
        GK_ptr = tl.advance(GK_ptr, (BLOCK_N, 0))
        V_ptr = tl.advance(V_ptr, (BLOCK_N, 0))
        
    # Finalize output
    acc = acc / l_i[:, None]
    
    # Store result
    Out_ptr = tl.make_block_ptr(
        base=Out + o_off,
        shape=(N_CTX, HEAD_DIM),
        strides=(som, son),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM),
        order=(1, 0)
    )
    tl.store(Out_ptr, acc.to(tl.float16))

def gdpa_attn(Q, K, V, GQ, GK):
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    # Grid definition: tiles along M dimension, and batch*heads
    grid = (triton.cdiv(M, 128), Z * H)
    
    gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        BLOCK_M=128, BLOCK_N=64, HEAD_DIM=64,
        num_warps=4, num_stages=2
    )
    
    return Out
"""
        }
