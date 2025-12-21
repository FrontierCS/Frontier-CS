import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attention_fwd_kernel(
    Q, K, V, O,
    row_lens_ptr,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    HAS_DV_TILE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptrs = K + offs_n[None, :] * stride_km + offs_d[:, None] * stride_kd
    v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
    
    row_lens_ptrs = row_lens_ptr + offs_m
    row_len = tl.load(row_lens_ptrs, mask=offs_m < M, other=0)
    
    max_row_len = tl.max(row_len)
    if max_row_len <= 0:
        return
    
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    start_n = 0
    for start_n in range(0, max_row_len, BLOCK_N):
        offs_n_cur = start_n + tl.arange(0, BLOCK_N)
        
        k = tl.load(
            k_ptrs, 
            mask=(offs_n_cur[None, :] < N) & (offs_d[:, None] < D), 
            other=0.0
        ).to(tl.float32)
        
        # Compute attention scores
        s = tl.dot(q, k) * (1.0 / math.sqrt(D))
        
        # Mask based on row lengths
        mask_n = offs_n_cur[None, :] < row_len[:, None]
        mask_m = offs_m[:, None] < M
        mask = mask_n & mask_m
        
        # Apply mask
        s = tl.where(mask, s, float('-inf'))
        
        # Streaming softmax update
        m_ij = tl.max(s, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        
        p = tl.exp(s - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        if HAS_DV_TILE:
            v = tl.load(
                v_ptrs, 
                mask=(offs_n_cur[:, None] < N) & (offs_dv[None, :] < Dv), 
                other=0.0
            ).to(tl.float32)
            
            # Update accumulation with proper scaling
            acc = acc * alpha[:, None]
            p_scaled = p.to(v.dtype)
            acc += tl.dot(p_scaled, v)
        else:
            # Alternative handling for small Dv
            v = tl.load(
                v_ptrs,
                mask=offs_n_cur[:, None] < N,
                other=0.0
            ).to(tl.float32)
            
            acc = acc * alpha[:, None]
            p_scaled = p.to(v.dtype)
            acc += tl.dot(p_scaled, v)
        
        m_i = m_i_new
    
    # Final normalization
    acc = acc / l_i[:, None]
    
    # Store output
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(
        o_ptrs, 
        acc.to(tl.float16), 
        mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    )

@triton.jit
def _ragged_attention_fwd_kernel_small_d(
    Q, K, V, O,
    row_lens_ptr,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, Dv)
    
    row_lens_ptrs = row_lens_ptr + offs_m
    row_len = tl.load(row_lens_ptrs, mask=offs_m < M, other=0)
    
    max_row_len = tl.max(row_len)
    if max_row_len <= 0:
        return
    
    # Load Q matrix
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    
    start_n = 0
    for start_n in range(0, max_row_len, BLOCK_N):
        offs_n_cur = start_n + tl.arange(0, BLOCK_N)
        
        # Load K matrix
        k_ptrs = K + offs_n_cur[None, :] * stride_km + offs_d[:, None] * stride_kd
        k = tl.load(
            k_ptrs,
            mask=(offs_n_cur[None, :] < N) & (offs_d[:, None] < D),
            other=0.0
        ).to(tl.float32)
        
        # Load V matrix
        v_ptrs = V + offs_n_cur[:, None] * stride_vm + offs_dv[None, :] * stride_vd
        v = tl.load(
            v_ptrs,
            mask=(offs_n_cur[:, None] < N) & (offs_dv[None, :] < Dv),
            other=0.0
        ).to(tl.float32)
        
        # Compute attention scores
        s = tl.dot(q, k) * (1.0 / math.sqrt(D))
        
        # Mask based on row lengths
        mask_n = offs_n_cur[None, :] < row_len[:, None]
        mask_m = offs_m[:, None] < M
        mask = mask_n & mask_m
        
        s = tl.where(mask, s, float('-inf'))
        
        # Streaming softmax
        m_ij = tl.max(s, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        
        p = tl.exp(s - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        # Update accumulation
        acc = acc * alpha[:, None]
        p_scaled = p.to(v.dtype)
        acc += tl.dot(p_scaled, v)
        
        m_i = m_i_new
    
    # Final normalization and store
    acc = acc / l_i[:, None]
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(
        o_ptrs,
        acc.to(tl.float16),
        mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    )

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), 1)
    
    if Dv <= 64:
        BLOCK_M = 4 if M >= 512 else 2
        BLOCK_N = 128 if N >= 1024 else 64
        BLOCK_D = D
        
        _ragged_attention_fwd_kernel_small_d[grid](
            Q, K, V, O,
            row_lens,
            Q.stride(0), Q.stride(1),
            K.stride(0), K.stride(1),
            V.stride(0), V.stride(1),
            O.stride(0), O.stride(1),
            M, N, D, Dv,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_D=BLOCK_D,
        )
    else:
        BLOCK_M = 4
        BLOCK_N = 64
        BLOCK_D = D
        BLOCK_DV = min(64, Dv)
        
        grid_large = lambda META: (
            triton.cdiv(M, META['BLOCK_M']),
            triton.cdiv(Dv, META['BLOCK_DV'])
        )
        
        HAS_DV_TILE = Dv > BLOCK_DV
        
        _ragged_attention_fwd_kernel[grid_large](
            Q, K, V, O,
            row_lens,
            Q.stride(0), Q.stride(1),
            K.stride(0), K.stride(1),
            V.stride(0), V.stride(1),
            O.stride(0), O.stride(1),
            M, N, D, Dv,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_D=BLOCK_D,
            BLOCK_DV=BLOCK_DV,
            HAS_DV_TILE=HAS_DV_TILE,
        )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attention_fwd_kernel(
    Q, K, V, O,
    row_lens_ptr,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    HAS_DV_TILE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptrs = K + offs_n[None, :] * stride_km + offs_d[:, None] * stride_kd
    v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
    
    row_lens_ptrs = row_lens_ptr + offs_m
    row_len = tl.load(row_lens_ptrs, mask=offs_m < M, other=0)
    
    max_row_len = tl.max(row_len)
    if max_row_len <= 0:
        return
    
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    start_n = 0
    for start_n in range(0, max_row_len, BLOCK_N):
        offs_n_cur = start_n + tl.arange(0, BLOCK_N)
        
        k = tl.load(
            k_ptrs, 
            mask=(offs_n_cur[None, :] < N) & (offs_d[:, None] < D), 
            other=0.0
        ).to(tl.float32)
        
        s = tl.dot(q, k) * (1.0 / math.sqrt(D))
        
        mask_n = offs_n_cur[None, :] < row_len[:, None]
        mask_m = offs_m[:, None] < M
        mask = mask_n & mask_m
        
        s = tl.where(mask, s, float('-inf'))
        
        m_ij = tl.max(s, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        
        p = tl.exp(s - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        if HAS_DV_TILE:
            v = tl.load(
                v_ptrs, 
                mask=(offs_n_cur[:, None] < N) & (offs_dv[None, :] < Dv), 
                other=0.0
            ).to(tl.float32)
            
            acc = acc * alpha[:, None]
            p_scaled = p.to(v.dtype)
            acc += tl.dot(p_scaled, v)
        else:
            v = tl.load(
                v_ptrs,
                mask=offs_n_cur[:, None] < N,
                other=0.0
            ).to(tl.float32)
            
            acc = acc * alpha[:, None]
            p_scaled = p.to(v.dtype)
            acc += tl.dot(p_scaled, v)
        
        m_i = m_i_new
    
    acc = acc / l_i[:, None]
    
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(
        o_ptrs, 
        acc.to(tl.float16), 
        mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    )

@triton.jit
def _ragged_attention_fwd_kernel_small_d(
    Q, K, V, O,
    row_lens_ptr,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, Dv)
    
    row_lens_ptrs = row_lens_ptr + offs_m
    row_len = tl.load(row_lens_ptrs, mask=offs_m < M, other=0)
    
    max_row_len = tl.max(row_len)
    if max_row_len <= 0:
        return
    
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    
    start_n = 0
    for start_n in range(0, max_row_len, BLOCK_N):
        offs_n_cur = start_n + tl.arange(0, BLOCK_N)
        
        k_ptrs = K + offs_n_cur[None, :] * stride_km + offs_d[:, None] * stride_kd
        k = tl.load(
            k_ptrs,
            mask=(offs_n_cur[None, :] < N) & (offs_d[:, None] < D),
            other=0.0
        ).to(tl.float32)
        
        v_ptrs = V + offs_n_cur[:, None] * stride_vm + offs_dv[None, :] * stride_vd
        v = tl.load(
            v_ptrs,
            mask=(offs_n_cur[:, None] < N) & (offs_dv[None, :] < Dv),
            other=0.0
        ).to(tl.float32)
        
        s = tl.dot(q, k) * (1.0 / math.sqrt(D))
        
        mask_n = offs_n_cur[None, :] < row_len[:, None]
        mask_m = offs_m[:, None] < M
        mask = mask_n & mask_m
        
        s = tl.where(mask, s, float('-inf'))
        
        m_ij = tl.max(s, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        
        p = tl.exp(s - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        acc = acc * alpha[:, None]
        p_scaled = p.to(v.dtype)
        acc += tl.dot(p_scaled, v)
        
        m_i = m_i_new
    
    acc = acc / l_i[:, None]
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(
        o_ptrs,
        acc.to(tl.float16),
        mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    )

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), 1)
    
    if Dv <= 64:
        BLOCK_M = 4 if M >= 512 else 2
        BLOCK_N = 128 if N >= 1024 else 64
        BLOCK_D = D
        
        _ragged_attention_fwd_kernel_small_d[grid](
            Q, K, V, O,
            row_lens,
            Q.stride(0), Q.stride(1),
            K.stride(0), K.stride(1),
            V.stride(0), V.stride(1),
            O.stride(0), O.stride(1),
            M, N, D, Dv,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_D=BLOCK_D,
        )
    else:
        BLOCK_M = 4
        BLOCK_N = 64
        BLOCK_D = D
        BLOCK_DV = min(64, Dv)
        
        grid_large = lambda META: (
            triton.cdiv(M, META['BLOCK_M']),
            triton.cdiv(Dv, META['BLOCK_DV'])
        )
        
        HAS_DV_TILE = Dv > BLOCK_DV
        
        _ragged_attention_fwd_kernel[grid_large](
            Q, K, V, O,
            row_lens,
            Q.stride(0), Q.stride(1),
            K.stride(0), K.stride(1),
            V.stride(0), V.stride(1),
            O.stride(0), O.stride(1),
            M, N, D, Dv,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_D=BLOCK_D,
            BLOCK_DV=BLOCK_DV,
            HAS_DV_TILE=HAS_DV_TILE,
        )
    
    return O
"""
        }
