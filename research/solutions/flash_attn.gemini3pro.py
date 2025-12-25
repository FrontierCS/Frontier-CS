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
def _flash_attn_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    sm_scale,
    Z, H, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    # Grid: (M // BLOCK_M, Z * H)
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_h = off_hz % H
    off_z = off_hz // H
    
    # Calculate offsets for the batch/head
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh

    # Create block pointers
    # Q: (M, D)
    Q_ptr = tl.make_block_ptr(
        base=Q + q_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_qm, stride_qk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DMODEL),
        order=(1, 0)
    )
    
    # K: (N, D)
    K_ptr = tl.make_block_ptr(
        base=K + k_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_kn, stride_kk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, BLOCK_DMODEL),
        order=(1, 0)
    )
    
    # V: (N, D)
    V_ptr = tl.make_block_ptr(
        base=V + v_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_vn, stride_vk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, BLOCK_DMODEL),
        order=(1, 0)
    )
    
    # Initialize accumulators
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32) + 1.0
    
    # Load Q once
    q = tl.load(Q_ptr)
    
    # Determine loop bounds
    lo = 0
    # For causal, we only need to iterate up to the current block of M
    hi = (start_m + 1) * BLOCK_M if IS_CAUSAL else N_CTX
    if hi > N_CTX:
        hi = N_CTX
        
    for start_n in range(lo, hi, BLOCK_N):
        # Load K, V
        k = tl.load(K_ptr)
        v = tl.load(V_ptr)
        
        # Compute QK^T
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Apply Causal Mask
        if IS_CAUSAL:
            offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
            offs_n = start_n + tl.arange(0, BLOCK_N)
            # Mask where column index > row index
            mask = offs_m[:, None] >= offs_n[None, :]
            qk = tl.where(mask, qk, float("-inf"))
            
        # Online Softmax
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        # Update accumulators
        m_new = tl.max(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v) * beta[:, None]
        l_i = l_i * alpha + l_ij * beta
        m_i = m_new
        
        # Advance K, V pointers
        K_ptr = tl.advance(K_ptr, (BLOCK_N, 0))
        V_ptr = tl.advance(V_ptr, (BLOCK_N, 0))
        
    # Finalize
    acc = acc / l_i[:, None]
    
    # Store Output
    O_ptr = tl.make_block_ptr(
        base=Out + o_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_om, stride_on),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DMODEL),
        order=(1, 0)
    )
    tl.store(O_ptr, acc.to(tl.float16))

def flash_attn(Q, K, V, causal=True):
    # Shape checking
    Z, H, M, D = Q.shape
    # K, V are (Z, H, N, D)
    
    O = torch.empty_like(Q)
    
    # Tuning parameters for L4
    BLOCK_M = 128
    BLOCK_N = 64
    num_warps = 4
    num_stages = 2
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    sm_scale = 1.0 / (D ** 0.5)
    
    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
        Z, H, M,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=D,
        IS_CAUSAL=causal,
        num_warps=num_warps,
        num_stages=num_stages
    )
    return O
"""
        return {"code": code}
