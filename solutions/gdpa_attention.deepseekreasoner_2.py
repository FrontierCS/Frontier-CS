import torch
import triton
import triton.language as tl


@triton.jit
def _gdpa_attn_fwd_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch = pid_bh // H
    head = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    m_mask = offs_m < M
    
    q_ptr = Q + batch * stride_qz + head * stride_qh
    k_ptr = K + batch * stride_kz + head * stride_kh
    v_ptr = V + batch * stride_vz + head * stride_vh
    gq_ptr = GQ + batch * stride_gqz + head * stride_gqh
    gk_ptr = GK + batch * stride_gkz + head * stride_gkh
    out_ptr = Out + batch * stride_oz + head * stride_oh
    
    if USE_BLOCK_PTR:
        q_block_ptr = tl.make_block_ptr(
            base=q_ptr,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        gq_block_ptr = tl.make_block_ptr(
            base=gq_ptr,
            shape=(M, Dq),
            strides=(stride_gqm, stride_gqd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
    else:
        q_ptrs = q_ptr + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
        gq_ptrs = gq_ptr + (offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
    
    if USE_BLOCK_PTR:
        q_block = tl.load(q_block_ptr, boundary_check=(0, 1), padding_option="zero")
        gq_block = tl.load(gq_block_ptr, boundary_check=(0, 1), padding_option="zero")
        q_gated = q_block * tl.sigmoid(gq_block)
    else:
        q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
        gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0)
        q_gated = q * tl.sigmoid(gq)
    
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    scale = 1.0 / tl.sqrt(tl.cast(Dq, tl.float32))
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        if USE_BLOCK_PTR:
            k_block_ptr = tl.make_block_ptr(
                base=k_ptr,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            gk_block_ptr = tl.make_block_ptr(
                base=gk_ptr,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkd),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            v_block_ptr = tl.make_block_ptr(
                base=v_ptr,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            
            k_block = tl.load(k_block_ptr, boundary_check=(0, 1), padding_option="zero")
            gk_block = tl.load(gk_block_ptr, boundary_check=(0, 1), padding_option="zero")
            k_gated = k_block * tl.sigmoid(gk_block)
            v_block = tl.load(v_block_ptr, boundary_check=(0, 1), padding_option="zero")
        else:
            n_mask = (start_n + offs_n) < N
            k_ptrs = k_ptr + ((start_n + offs_n[:, None]) * stride_kn + offs_dq[None, :] * stride_kd)
            gk_ptrs = gk_ptr + ((start_n + offs_n[:, None]) * stride_gkn + offs_dq[None, :] * stride_gkd)
            v_ptrs = v_ptr + ((start_n + offs_n[:, None]) * stride_vn + offs_dv[None, :] * stride_vd)
            
            k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)
            gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0)
            k_gated = k * tl.sigmoid(gk)
            v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        
        qk = tl.dot(q_gated, tl.trans(k_gated))
        qk = qk * scale
        
        qk = tl.where(m_mask[:, None] & n_mask[None, :], qk, float("-inf"))
        
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_new = alpha * l_i + beta * l_ij
        
        acc_scale = l_i / l_new * alpha
        acc = acc * acc_scale[:, None]
        
        p_scale = beta / l_new
        p = p * p_scale[:, None]
        
        if USE_BLOCK_PTR:
            acc += tl.dot(p.to(v_block.dtype), v_block)
        else:
            acc += tl.dot(p.to(v.dtype), v)
        
        m_i = m_new
        l_i = l_new
    
    if USE_BLOCK_PTR:
        out_block_ptr = tl.make_block_ptr(
            base=out_ptr,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
        tl.store(out_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))
    else:
        out_ptrs = out_ptr + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
        tl.store(out_ptrs, acc.to(tl.float16), mask=m_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    grid = (Z * H, triton.cdiv(M, 64))
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    USE_BLOCK_PTR = M % BLOCK_M == 0 and N % BLOCK_N == 0 and Dq % BLOCK_Dq == 0 and Dv % BLOCK_Dv == 0
    
    _gdpa_attn_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
        num_warps=4,
        num_stages=3,
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl


@triton.jit
def _gdpa_attn_fwd_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch = pid_bh // H
    head = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    m_mask = offs_m < M
    
    q_ptr = Q + batch * stride_qz + head * stride_qh
    k_ptr = K + batch * stride_kz + head * stride_kh
    v_ptr = V + batch * stride_vz + head * stride_vh
    gq_ptr = GQ + batch * stride_gqz + head * stride_gqh
    gk_ptr = GK + batch * stride_gkz + head * stride_gkh
    out_ptr = Out + batch * stride_oz + head * stride_oh
    
    if USE_BLOCK_PTR:
        q_block_ptr = tl.make_block_ptr(
            base=q_ptr,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        gq_block_ptr = tl.make_block_ptr(
            base=gq_ptr,
            shape=(M, Dq),
            strides=(stride_gqm, stride_gqd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
    else:
        q_ptrs = q_ptr + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
        gq_ptrs = gq_ptr + (offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
    
    if USE_BLOCK_PTR:
        q_block = tl.load(q_block_ptr, boundary_check=(0, 1), padding_option="zero")
        gq_block = tl.load(gq_block_ptr, boundary_check=(0, 1), padding_option="zero")
        q_gated = q_block * tl.sigmoid(gq_block)
    else:
        q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
        gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0)
        q_gated = q * tl.sigmoid(gq)
    
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    scale = 1.0 / tl.sqrt(tl.cast(Dq, tl.float32))
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        if USE_BLOCK_PTR:
            k_block_ptr = tl.make_block_ptr(
                base=k_ptr,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            gk_block_ptr = tl.make_block_ptr(
                base=gk_ptr,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkd),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            v_block_ptr = tl.make_block_ptr(
                base=v_ptr,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(start_n, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            
            k_block = tl.load(k_block_ptr, boundary_check=(0, 1), padding_option="zero")
            gk_block = tl.load(gk_block_ptr, boundary_check=(0, 1), padding_option="zero")
            k_gated = k_block * tl.sigmoid(gk_block)
            v_block = tl.load(v_block_ptr, boundary_check=(0, 1), padding_option="zero")
        else:
            n_mask = (start_n + offs_n) < N
            k_ptrs = k_ptr + ((start_n + offs_n[:, None]) * stride_kn + offs_dq[None, :] * stride_kd)
            gk_ptrs = gk_ptr + ((start_n + offs_n[:, None]) * stride_gkn + offs_dq[None, :] * stride_gkd)
            v_ptrs = v_ptr + ((start_n + offs_n[:, None]) * stride_vn + offs_dv[None, :] * stride_vd)
            
            k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)
            gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0)
            k_gated = k * tl.sigmoid(gk)
            v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        
        qk = tl.dot(q_gated, tl.trans(k_gated))
        qk = qk * scale
        
        qk = tl.where(m_mask[:, None] & n_mask[None, :], qk, float("-inf"))
        
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_new = alpha * l_i + beta * l_ij
        
        acc_scale = l_i / l_new * alpha
        acc = acc * acc_scale[:, None]
        
        p_scale = beta / l_new
        p = p * p_scale[:, None]
        
        if USE_BLOCK_PTR:
            acc += tl.dot(p.to(v_block.dtype), v_block)
        else:
            acc += tl.dot(p.to(v.dtype), v)
        
        m_i = m_new
        l_i = l_new
    
    if USE_BLOCK_PTR:
        out_block_ptr = tl.make_block_ptr(
            base=out_ptr,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
        tl.store(out_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))
    else:
        out_ptrs = out_ptr + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
        tl.store(out_ptrs, acc.to(tl.float16), mask=m_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    grid = (Z * H, triton.cdiv(M, 64))
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    USE_BLOCK_PTR = M % BLOCK_M == 0 and N % BLOCK_N == 0 and Dq % BLOCK_Dq == 0 and Dv % BLOCK_Dv == 0
    
    _gdpa_attn_fwd_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
        num_warps=4,
        num_stages=3,
    )
    
    return Out
"""}
