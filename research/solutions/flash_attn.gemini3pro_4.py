import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
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
    BLOCK_DMODEL: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    batch_id = off_hz // H
    head_id = off_hz % H
    
    # Base pointers
    Q_ptr = Q + batch_id * stride_qz + head_id * stride_qh
    K_ptr = K + batch_id * stride_kz + head_id * stride_kh
    V_ptr = V + batch_id * stride_vz + head_id * stride_vh
    O_ptr = Out + batch_id * stride_oz + head_id * stride_oh
    
    # Block offsets
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    # Load Q
    q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk)
    mask_m = offs_m < N_CTX
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Scale Q
    q = q * sm_scale
    
    # Init Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)
    
    # Loop bounds
    lo = 0
    hi = 0
    if IS_CAUSAL:
        hi = (start_m + 1) * BLOCK_M
    else:
        hi = N_CTX
        
    for start_n in range(lo, hi, BLOCK_N):
        if start_n >= N_CTX:
            break
            
        k_cols = start_n + offs_n
        mask_k = k_cols < N_CTX
        
        # Load K
        k_ptrs = K_ptr + (k_cols[:, None] * stride_kn + offs_d[None, :] * stride_kk)
        k = tl.load(k_ptrs, mask=mask_k[:, None], other=0.0)
        
        # Compute QK^T
        qk = tl.dot(q, tl.trans(k))
        
        # Causal Masking
        if IS_CAUSAL:
            # Check if block is fully valid (left of diagonal)
            # Min row: start_m * BLOCK_M
            # Max col: start_n + BLOCK_N - 1
            if start_n + BLOCK_N <= start_m * BLOCK_M:
                pass
            else:
                causal_mask = offs_m[:, None] >= k_cols[None, :]
                qk = tl.where(causal_mask, qk, float("-inf"))
        
        # Online Softmax
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        # Update stats
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        # Load V
        v_ptrs = V_ptr + (k_cols[:, None] * stride_vn + offs_d[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=mask_k[:, None], other=0.0)
        
        # Update accumulator
        acc = acc * alpha[:, None]
        acc += tl.dot(p.to(tl.float16), v) * beta[:, None]
        
        l_i = l_i * alpha + l_ij * beta
        m_i = m_new
        
    # Finalize
    acc = acc / l_i[:, None]
    
    # Store
    o_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_d[None, :] * stride_on)
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None])

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    # Q: (Z, H, M, D)
    Z, H, M, D = Q.shape
    O = torch.empty_like(Q)
    
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DMODEL = D
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    sm_scale = 1.0 / (D ** 0.5)
    
    num_warps = 4
    num_stages = 4
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        IS_CAUSAL=causal,
        num_warps=num_warps,
        num_stages=num_stages
    )
    return O
"""
        return {"code": code}
