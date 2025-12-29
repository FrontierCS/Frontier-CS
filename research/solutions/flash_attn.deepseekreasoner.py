import torch
import triton
import triton.language as tl


@triton.jit
def _fwd_kernel(
    Q, K, V, sm_scale, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_ok,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh
    
    m_start = start_m * BLOCK_M
    m_end = m_start + BLOCK_M
    
    m_blocks = tl.cdiv(M, BLOCK_M)
    n_blocks = tl.cdiv(N, BLOCK_N)
    
    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_ptrs = Q + q_offset + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    k_ptrs = K + k_offset + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
    v_ptrs = V + v_offset + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk
    
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    for block_n in range(n_blocks):
        n_start = block_n * BLOCK_N
        n_end = n_start + BLOCK_N
        
        if CAUSAL:
            causal_mask = (m_start + tl.arange(0, BLOCK_M))[:, None] >= (n_start + tl.arange(0, BLOCK_N))[None, :]
        
        k = tl.load(k_ptrs + n_start * stride_kn, mask=(n_start + offs_n)[:, None] < N, other=0.0)
        v = tl.load(v_ptrs + n_start * stride_vn, mask=(n_start + offs_n)[:, None] < N, other=0.0)
        
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        
        s = tl.dot(q, tl.trans(k))
        s *= sm_scale
        
        if CAUSAL:
            s = tl.where(causal_mask, s, float("-inf"))
        
        m_ij = tl.max(s, 1)
        p = tl.exp(s - m_ij[:, None])
        
        l_ij = tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij)
        acc = acc * alpha[:, None]
        
        p = p.to(v.dtype)
        acc += tl.dot(p, v)
        
        m_i = m_ij
        l_i = l_i * alpha + l_ij
    
    acc = acc / l_i[:, None]
    
    out_ptrs = Out + o_offset + offs_m[:, None] * stride_om + offs_d[None, :] * stride_ok
    tl.store(out_ptrs, acc, mask=offs_m[:, None] < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    assert K.shape == (Z, H, N, Dq)
    assert V.shape == (Z, H, N, Dv)
    
    sm_scale = 1.0 / (Dq ** 0.5)
    
    Out = torch.empty_like(Q[:, :, :, :Dv])
    
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = min(64, Dv)
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _fwd_kernel[grid](
        Q, K, V, sm_scale, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        CAUSAL=causal,
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl


@triton.jit
def _fwd_kernel(
    Q, K, V, sm_scale, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_ok,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh
    
    m_start = start_m * BLOCK_M
    m_end = m_start + BLOCK_M
    
    m_blocks = tl.cdiv(M, BLOCK_M)
    n_blocks = tl.cdiv(N, BLOCK_N)
    
    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_ptrs = Q + q_offset + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    k_ptrs = K + k_offset + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
    v_ptrs = V + v_offset + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk
    
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    for block_n in range(n_blocks):
        n_start = block_n * BLOCK_N
        n_end = n_start + BLOCK_N
        
        if CAUSAL:
            causal_mask = (m_start + tl.arange(0, BLOCK_M))[:, None] >= (n_start + tl.arange(0, BLOCK_N))[None, :]
        
        k = tl.load(k_ptrs + n_start * stride_kn, mask=(n_start + offs_n)[:, None] < N, other=0.0)
        v = tl.load(v_ptrs + n_start * stride_vn, mask=(n_start + offs_n)[:, None] < N, other=0.0)
        
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        
        s = tl.dot(q, tl.trans(k))
        s *= sm_scale
        
        if CAUSAL:
            s = tl.where(causal_mask, s, float("-inf"))
        
        m_ij = tl.max(s, 1)
        p = tl.exp(s - m_ij[:, None])
        
        l_ij = tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij)
        acc = acc * alpha[:, None]
        
        p = p.to(v.dtype)
        acc += tl.dot(p, v)
        
        m_i = m_ij
        l_i = l_i * alpha + l_ij
    
    acc = acc / l_i[:, None]
    
    out_ptrs = Out + o_offset + offs_m[:, None] * stride_om + offs_d[None, :] * stride_ok
    tl.store(out_ptrs, acc, mask=offs_m[:, None] < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    assert K.shape == (Z, H, N, Dq)
    assert V.shape == (Z, H, N, Dv)
    
    sm_scale = 1.0 / (Dq ** 0.5)
    
    Out = torch.empty_like(Q[:, :, :, :Dv])
    
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = min(64, Dv)
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _fwd_kernel[grid](
        Q, K, V, sm_scale, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        CAUSAL=causal,
    )
    
    return Out
"""}