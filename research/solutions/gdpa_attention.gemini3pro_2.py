import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
import math

@triton.jit
def gdpa_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, M, N,
    sm_scale,
    BLOCK_M: tl.constexpr, 
    BLOCK_N: tl.constexpr, 
    DQ: tl.constexpr, 
    DV: tl.constexpr
):
    # Grid handling
    off_m = tl.program_id(0) * BLOCK_M
    off_zh = tl.program_id(1)
    off_z = off_zh // H
    off_h = off_zh % H
    
    # Base pointers for the current batch and head
    q_base = Q + off_z * stride_qz + off_h * stride_qh
    k_base = K + off_z * stride_kz + off_h * stride_kh
    v_base = V + off_z * stride_vz + off_h * stride_vh
    gq_base = GQ + off_z * stride_qz + off_h * stride_qh
    gk_base = GK + off_z * stride_kz + off_h * stride_kh
    out_base = Out + off_z * stride_oz + off_h * stride_oh

    # Initialize pointers using make_block_ptr
    # Q and GQ: Shape (M, DQ), contiguous in DQ (row-major)
    q_ptr = tl.make_block_ptr(
        base=q_base,
        shape=(M, DQ),
        strides=(stride_qm, stride_qk),
        offsets=(off_m, 0),
        block_shape=(BLOCK_M, DQ),
        order=(1, 0)
    )
    gq_ptr = tl.make_block_ptr(
        base=gq_base,
        shape=(M, DQ),
        strides=(stride_qm, stride_qk),
        offsets=(off_m, 0),
        block_shape=(BLOCK_M, DQ),
        order=(1, 0)
    )
    
    # K and GK: Shape (N, DQ) in memory.
    # We load them as (DQ, N) blocks to perform Q @ K.T directly as dot(Q, K_transposed_block).
    # Strides for (DQ, N) view are (stride_kk, stride_kn).
    k_ptr = tl.make_block_ptr(
        base=k_base,
        shape=(DQ, N),
        strides=(stride_kk, stride_kn),
        offsets=(0, 0),
        block_shape=(DQ, BLOCK_N),
        order=(0, 1)
    )
    gk_ptr = tl.make_block_ptr(
        base=gk_base,
        shape=(DQ, N),
        strides=(stride_kk, stride_kn),
        offsets=(0, 0),
        block_shape=(DQ, BLOCK_N),
        order=(0, 1)
    )
    
    # V: Shape (N, DV), contiguous in DV
    v_ptr = tl.make_block_ptr(
        base=v_base,
        shape=(N, DV),
        strides=(stride_vn, stride_vk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, DV),
        order=(1, 0)
    )

    # Load Q and GQ
    # Assuming M is a multiple of BLOCK_M based on problem spec (512, 1024), 
    # so boundary checks are skipped for performance.
    q = tl.load(q_ptr)
    gq = tl.load(gq_ptr)
    
    # Apply Query Gating: Qg = Q * sigmoid(GQ)
    q = q * tl.sigmoid(gq)
    
    # Initialize statistics for online softmax
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, DV], dtype=tl.float32)
    
    # Loop over K/V blocks
    # N is also multiple of BLOCK_N (N=M)
    for start_n in range(0, N, BLOCK_N):
        # Load K, GK
        k = tl.load(k_ptr)
        gk = tl.load(gk_ptr)
        
        # Apply Key Gating: Kg = K * sigmoid(GK)
        # k, gk are loaded as (DQ, BLOCK_N). Operation is elementwise.
        k = k * tl.sigmoid(gk)
        
        # Load V
        v = tl.load(v_ptr)
        
        # Compute Attention Scores: S = Qg @ Kg.T
        # q: (BLOCK_M, DQ), k: (DQ, BLOCK_N) -> qk: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, k)
        
        # Apply scaling
        qk *= sm_scale
        
        # Online Softmax updates
        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        # Update denominator
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # Update output accumulator
        # acc: (BLOCK_M, DV), p: (BLOCK_M, BLOCK_N), v: (BLOCK_N, DV)
        # Accumulate in fp32
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        
        # Update max
        m_i = m_new
        
        # Advance pointers
        k_ptr = tl.advance(k_ptr, (0, BLOCK_N))
        gk_ptr = tl.advance(gk_ptr, (0, BLOCK_N))
        v_ptr = tl.advance(v_ptr, (BLOCK_N, 0))
        
    # Finalize Output
    acc = acc / l_i[:, None]
    
    # Store Output
    out_ptr = tl.make_block_ptr(
        base=out_base,
        shape=(M, DV),
        strides=(stride_om, stride_on),
        offsets=(off_m, 0),
        block_shape=(BLOCK_M, DV),
        order=(1, 0)
    )
    tl.store(out_ptr, acc.to(tl.float16))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    """
    # Input verification
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Output tensor allocation
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Kernel configuration
    # L4 GPU (Ada) usually handles 128x64 blocks well for fp16
    BLOCK_M = 128
    BLOCK_N = 64
    num_warps = 4
    num_stages = 3
    
    # Scaling factor
    sm_scale = 1.0 / math.sqrt(Dq)
    
    # Grid definition: (M tiles, Batch * Heads)
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    # Kernel Launch
    gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N,
        sm_scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        DQ=Dq,
        DV=Dv,
        num_warps=num_warps,
        num_stages=num_stages
    )
    
    return Out
'''
        return {"code": code}