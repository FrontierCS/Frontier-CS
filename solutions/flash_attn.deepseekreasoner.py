import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    IS_CAUSAL: tl.constexpr, SCALE: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch_id = pid_bh // H
    head_id = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_D)
    
    Q_ptr = Q + batch_id * stride_qz + head_id * stride_qh
    K_ptr = K + batch_id * stride_kz + head_id * stride_kh
    V_ptr = V + batch_id * stride_vz + head_id * stride_vh
    Out_ptr = Out + batch_id * stride_oz + head_id * stride_oh
    
    q_offset = offs_m[:, None] * stride_qm + offs_dq[None, :] * 1
    q_ptrs = Q_ptr + q_offset
    q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
    
    o = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    if IS_CAUSAL:
        start_n = tl.maximum(pid_m * BLOCK_M - (BLOCK_M - 1), 0)
    else:
        start_n = 0
    
    for start_n in range(start_n, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        k_offset = (start_n + offs_n)[None, :] * stride_kn + offs_dq[:, None] * 1
        k_ptrs = K_ptr + k_offset
        k = tl.load(k_ptrs, mask=(start_n + offs_n)[None, :] < N, other=0.0)
        
        qk = tl.dot(q, k, allow_tf32=False)
        qk = qk * SCALE
        
        if IS_CAUSAL:
            m = offs_m[:, None]
            n = start_n + offs_n[None, :]
            mask = m >= n
            qk = tl.where(mask, qk, float('-inf'))
        
        m_ij = tl.maximum(tl.max(qk, 1), m_i)
        m_ij = tl.where(m_i == float('-inf'), tl.max(qk, 1), m_ij)
        
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij
        
        v_offset = (start_n + offs_n)[:, None] * stride_vn + offs_dq[None, :] * 1
        v_ptrs = V_ptr + v_offset
        v = tl.load(v_ptrs, mask=(start_n + offs_n)[:, None] < N, other=0.0)
        
        p = p.to(v.dtype)
        o = o * alpha[:, None] + tl.dot(p, v, allow_tf32=False)
        m_i = m_ij
    
    o = o / l_i[:, None]
    o = o.to(tl.float16)
    
    out_offset = offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * 1
    out_ptrs = Out_ptr + out_offset
    tl.store(out_ptrs, o, mask=offs_m[:, None] < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.stride(3) == 1 and K.stride(3) == 1 and V.stride(3) == 1
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    if M >= 2048:
        BLOCK_M = 128
        BLOCK_N = 64
    elif M >= 1024:
        BLOCK_M = 128
        BLOCK_N = 64
    else:
        BLOCK_M = 64
        BLOCK_N = 64
    
    BLOCK_D = 64 if Dq % 64 == 0 else 32
    
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    scale = 1.0 / (Dq ** 0.5)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        IS_CAUSAL=causal, SCALE=scale,
        num_stages=3 if M <= 1024 else 4,
        num_warps=8 if BLOCK_D >= 64 else 4,
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    IS_CAUSAL: tl.constexpr, SCALE: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch_id = pid_bh // H
    head_id = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_D)
    
    Q_ptr = Q + batch_id * stride_qz + head_id * stride_qh
    K_ptr = K + batch_id * stride_kz + head_id * stride_kh
    V_ptr = V + batch_id * stride_vz + head_id * stride_vh
    Out_ptr = Out + batch_id * stride_oz + head_id * stride_oh
    
    q_offset = offs_m[:, None] * stride_qm + offs_dq[None, :] * 1
    q_ptrs = Q_ptr + q_offset
    q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
    
    o = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    if IS_CAUSAL:
        start_n = tl.maximum(pid_m * BLOCK_M - (BLOCK_M - 1), 0)
    else:
        start_n = 0
    
    for start_n in range(start_n, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        k_offset = (start_n + offs_n)[None, :] * stride_kn + offs_dq[:, None] * 1
        k_ptrs = K_ptr + k_offset
        k = tl.load(k_ptrs, mask=(start_n + offs_n)[None, :] < N, other=0.0)
        
        qk = tl.dot(q, k, allow_tf32=False)
        qk = qk * SCALE
        
        if IS_CAUSAL:
            m = offs_m[:, None]
            n = start_n + offs_n[None, :]
            mask = m >= n
            qk = tl.where(mask, qk, float('-inf'))
        
        m_ij = tl.maximum(tl.max(qk, 1), m_i)
        m_ij = tl.where(m_i == float('-inf'), tl.max(qk, 1), m_ij)
        
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij
        
        v_offset = (start_n + offs_n)[:, None] * stride_vn + offs_dq[None, :] * 1
        v_ptrs = V_ptr + v_offset
        v = tl.load(v_ptrs, mask=(start_n + offs_n)[:, None] < N, other=0.0)
        
        p = p.to(v.dtype)
        o = o * alpha[:, None] + tl.dot(p, v, allow_tf32=False)
        m_i = m_ij
    
    o = o / l_i[:, None]
    o = o.to(tl.float16)
    
    out_offset = offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * 1
    out_ptrs = Out_ptr + out_offset
    tl.store(out_ptrs, o, mask=offs_m[:, None] < M)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.stride(3) == 1 and K.stride(3) == 1 and V.stride(3) == 1
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    if M >= 2048:
        BLOCK_M = 128
        BLOCK_N = 64
    elif M >= 1024:
        BLOCK_M = 128
        BLOCK_N = 64
    else:
        BLOCK_M = 64
        BLOCK_N = 64
    
    BLOCK_D = 64 if Dq % 64 == 0 else 32
    
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    scale = 1.0 / (Dq ** 0.5)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        IS_CAUSAL=causal, SCALE=scale,
        num_stages=3 if M <= 1024 else 4,
        num_warps=8 if BLOCK_D >= 64 else 4,
    )
    
    return Out
'''
        return {"code": code}
