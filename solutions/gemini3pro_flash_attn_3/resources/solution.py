import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
    ],
    key=['N_CTX', 'BLOCK_DQ', 'BLOCK_DV'],
)
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
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    # Offsets for this head
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh
    
    # Tensor Pointers
    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = Out + o_offset
    
    # Range offsets
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Load Q
    # Q shape: (M, DQ)
    q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk)
    q_mask = offs_m[:, None] < N_CTX
    
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)
    
    # Initialize accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # Determine loop bound
    end_n = N_CTX
    if IS_CAUSAL:
        # Optimization: only loop up to the block containing the diagonal
        end_n = tl.minimum(end_n, (start_m + 1) * BLOCK_M)
    
    for start_n in range(0, end_n, BLOCK_N):
        cols = start_n + offs_n
        
        # Load K
        # K shape: (N, DQ)
        k_ptrs = K_ptr + (cols[:, None] * stride_kn + offs_dq[None, :] * stride_kk)
        k_mask = cols[:, None] < N_CTX
        
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)
        
        # Compute Attention Scores: QK^T
        # q: (BLOCK_M, DQ), k: (BLOCK_N, DQ) -> qk: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        
        # Causal Masking
        if IS_CAUSAL:
            mask = offs_m[:, None] >= cols[None, :]
            qk = tl.where(mask, qk, float("-inf"))
        
        # Online Softmax updates
        m_curr = tl.max(qk, 1) # (BLOCK_M,)
        
        p = tl.exp(qk - m_curr[:, None])
        l_curr = tl.sum(p, 1)
        
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_curr - m_new)
        
        l_i = l_i * alpha + l_curr * beta
        
        # Load V
        # V shape: (N, DV)
        v_ptrs = V_ptr + (cols[:, None] * stride_vn + offs_dv[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=k_mask, other=0.0)
        
        # Cast p to float16 for tensor core operation
        p = p.to(tl.float16)
        
        # Update accumulator
        # acc = acc * alpha + (p @ v) * beta
        acc = acc * alpha[:, None]
        pv = tl.dot(p, v)
        acc = acc + pv * beta[:, None]
        
        m_i = m_new

    # Epilogue: Normalize
    # Handle fully masked rows where l_i could be 0
    l_i = tl.where(l_i == 0.0, 1.0, l_i)
    acc = acc / l_i[:, None]
    
    # Store Output
    o_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_on)
    tl.store(o_ptrs, acc.to(tl.float16), mask=q_mask)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    # Grid definition
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    sm_scale = 1.0 / math.sqrt(Dq)
    
    _flash_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        sm_scale,
        Z, H, N,
        BLOCK_DQ=Dq,
        BLOCK_DV=Dv,
        IS_CAUSAL=causal
    )
    
    return Out
"""
        return {"code": code}
