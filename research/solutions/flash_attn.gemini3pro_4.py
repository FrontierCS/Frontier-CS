import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path=None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _attn_fwd_kernel(
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
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh
    
    # Block pointers
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    # Pointers
    q_ptrs = Q + q_offset + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    k_ptrs = K + k_offset + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kk
    v_ptrs = V + v_offset + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk
    
    # Load Q
    q = tl.load(q_ptrs)
    
    # Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)
    
    qk_scale = sm_scale
    
    # Loop bounds logic
    # If not causal: process 0 to N_CTX.
    # If causal: process 0 to (start_m + 1) * BLOCK_M.
    # Split into two loops: unmasked and masked.
    
    hi = N_CTX
    if IS_CAUSAL:
        hi = (start_m + 1) * BLOCK_M
        
    split_point = 0
    if IS_CAUSAL:
        split_point = start_m * BLOCK_M
        
    # Unmasked loop: [0, split_point)
    for start_n in range(0, split_point, BLOCK_N):
        k = tl.load(k_ptrs)
        v = tl.load(v_ptrs)
        
        qk = tl.dot(q, tl.trans(k))
        qk *= qk_scale
        
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        acc = acc * alpha[:, None]
        acc = tl.dot(p.to(tl.float16), v, acc=acc)
        
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_new
        
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn
        
    # Masked loop: [split_point, hi)
    for start_n in range(split_point, hi, BLOCK_N):
        k = tl.load(k_ptrs)
        v = tl.load(v_ptrs)
        
        qk = tl.dot(q, tl.trans(k))
        qk *= qk_scale
        
        if IS_CAUSAL:
            cur_offs_n = start_n + offs_n
            mask = offs_m[:, None] >= cur_offs_n[None, :]
            qk = tl.where(mask, qk, float('-inf'))
            
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        acc = acc * alpha[:, None]
        acc = tl.dot(p.to(tl.float16), v, acc=acc)
        
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_new
        
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn
    
    # Finalize and Store
    acc = acc / l_i[:, None]
    out_ptrs = Out + o_offset + offs_m[:, None] * stride_om + offs_d[None, :] * stride_on
    tl.store(out_ptrs, acc.to(tl.float16))

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DMODEL = D
    
    Out = torch.empty_like(Q)
    sm_scale = 1.0 / (D ** 0.5)
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, N,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL,
        IS_CAUSAL=causal,
        num_warps=4,
        num_stages=4
    )
    
    return Out
"""
        return {"code": code}