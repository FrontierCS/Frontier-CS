import torch
import triton
import triton.language as tl

@triton.jit
def _gdpa_attn_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_gqz, stride_gqh, stride_gqm, stride_gqk,
    stride_gkz, stride_gkh, stride_gkn, stride_gkk,
    stride_oz, stride_oh, stride_om, stride_ok,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch_idx = pid_bh // H
    head_idx = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_D)
    
    m_mask = offs_m < M
    dv_mask = offs_dv < Dv
    
    scale = 1.0 / tl.sqrt(tl.float32(Dq))
    
    q_ptrs = Q_ptr + batch_idx * stride_qz + head_idx * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk
    gq_ptrs = GQ_ptr + batch_idx * stride_gqz + head_idx * stride_gqh + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqk
    
    q_block = tl.load(q_ptrs, mask=m_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
    gq_block = tl.load(gq_ptrs, mask=m_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
    q_gated = q_block * tl.sigmoid(gq_block)
    
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        offs_n_curr = start_n + offs_n
        n_mask = offs_n_curr < N
        
        if USE_BLOCK_PTR:
            k_block_ptr = tl.make_block_ptr(
                base=K_ptr + batch_idx * stride_kz + head_idx * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kk),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            gk_block_ptr = tl.make_block_ptr(
                base=GK_ptr + batch_idx * stride_gkz + head_idx * stride_gkh,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkk),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            v_block_ptr = tl.make_block_ptr(
                base=V_ptr + batch_idx * stride_vz + head_idx * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vk),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            
            k_block = tl.load(k_block_ptr, boundary_check=(0, 1))
            gk_block = tl.load(gk_block_ptr, boundary_check=(0, 1))
            v_block = tl.load(v_block_ptr, boundary_check=(0, 1))
        else:
            k_ptrs = K_ptr + batch_idx * stride_kz + head_idx * stride_kh + offs_n_curr[:, None] * stride_kn + offs_dq[None, :] * stride_kk
            gk_ptrs = GK_ptr + batch_idx * stride_gkz + head_idx * stride_gkh + offs_n_curr[:, None] * stride_gkn + offs_dq[None, :] * stride_gkk
            v_ptrs = V_ptr + batch_idx * stride_vz + head_idx * stride_vh + offs_n_curr[:, None] * stride_vn + offs_dv[None, :] * stride_vk
            
            k_block = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
            gk_block = tl.load(gk_ptrs, mask=n_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
            v_block = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < Dv), other=0.0)
        
        k_gated = k_block * tl.sigmoid(gk_block)
        
        s = tl.dot(q_gated, tl.trans(k_gated)) * scale
        
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        p = tl.exp(s - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        p_v = tl.dot(p.to(v_block.dtype), v_block)
        
        acc = acc * tl.exp(m_i - m_ij)[:, None] * (l_i / l_ij)[:, None] + p_v / l_ij[:, None]
        
        m_i = m_ij
        l_i = l_ij
    
    out_ptrs = Out_ptr + batch_idx * stride_oz + head_idx * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ok
    tl.store(out_ptrs, acc, mask=m_mask[:, None] & dv_mask[None, :])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64
    
    USE_BLOCK_PTR = M >= 512 and N >= 512
    
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, out,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
        num_warps=4,
        num_stages=3,
    )
    
    return out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def _gdpa_attn_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    Z, H, M, N, Dq, Dv,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_gqz, stride_gqh, stride_gqm, stride_gqk,
    stride_gkz, stride_gkh, stride_gkn, stride_gkk,
    stride_oz, stride_oh, stride_om, stride_ok,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch_idx = pid_bh // H
    head_idx = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_D)
    
    m_mask = offs_m < M
    dv_mask = offs_dv < Dv
    
    scale = 1.0 / tl.sqrt(tl.float32(Dq))
    
    q_ptrs = Q_ptr + batch_idx * stride_qz + head_idx * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk
    gq_ptrs = GQ_ptr + batch_idx * stride_gqz + head_idx * stride_gqh + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqk
    
    q_block = tl.load(q_ptrs, mask=m_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
    gq_block = tl.load(gq_ptrs, mask=m_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
    q_gated = q_block * tl.sigmoid(gq_block)
    
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        offs_n_curr = start_n + offs_n
        n_mask = offs_n_curr < N
        
        if USE_BLOCK_PTR:
            k_block_ptr = tl.make_block_ptr(
                base=K_ptr + batch_idx * stride_kz + head_idx * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kk),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            gk_block_ptr = tl.make_block_ptr(
                base=GK_ptr + batch_idx * stride_gkz + head_idx * stride_gkh,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkk),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            v_block_ptr = tl.make_block_ptr(
                base=V_ptr + batch_idx * stride_vz + head_idx * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vk),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            
            k_block = tl.load(k_block_ptr, boundary_check=(0, 1))
            gk_block = tl.load(gk_block_ptr, boundary_check=(0, 1))
            v_block = tl.load(v_block_ptr, boundary_check=(0, 1))
        else:
            k_ptrs = K_ptr + batch_idx * stride_kz + head_idx * stride_kh + offs_n_curr[:, None] * stride_kn + offs_dq[None, :] * stride_kk
            gk_ptrs = GK_ptr + batch_idx * stride_gkz + head_idx * stride_gkh + offs_n_curr[:, None] * stride_gkn + offs_dq[None, :] * stride_gkk
            v_ptrs = V_ptr + batch_idx * stride_vz + head_idx * stride_vh + offs_n_curr[:, None] * stride_vn + offs_dv[None, :] * stride_vk
            
            k_block = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
            gk_block = tl.load(gk_ptrs, mask=n_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
            v_block = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < Dv), other=0.0)
        
        k_gated = k_block * tl.sigmoid(gk_block)
        
        s = tl.dot(q_gated, tl.trans(k_gated)) * scale
        
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        p = tl.exp(s - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        p_v = tl.dot(p.to(v_block.dtype), v_block)
        
        acc = acc * tl.exp(m_i - m_ij)[:, None] * (l_i / l_ij)[:, None] + p_v / l_ij[:, None]
        
        m_i = m_ij
        l_i = l_ij
    
    out_ptrs = Out_ptr + batch_idx * stride_oz + head_idx * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ok
    tl.store(out_ptrs, acc, mask=m_mask[:, None] & dv_mask[None, :])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64
    
    USE_BLOCK_PTR = M >= 512 and N >= 512
    
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, out,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
        num_warps=4,
        num_stages=3,
    )
    
    return out
'''
        return {"code": code}