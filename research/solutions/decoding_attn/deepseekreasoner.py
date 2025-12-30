import torch
import triton
import triton.language as tl
from typing import Optional
import os

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 128, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 128, 'num_warps': 8}),
    ],
    key=['M', 'N', 'Dq'],
)
@triton.jit
def _decoding_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_offset = pid_batch * stride_qz + pid_head * stride_qh + offs_m[:, None] * stride_qm
    Q_ptrs = Q_ptr + q_offset + offs_d[None, :] * stride_qd
    
    k_offset_base = pid_batch * stride_kz + pid_head * stride_kh
    v_offset_base = pid_batch * stride_vz + pid_head * stride_vh
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        k_offset = k_offset_base + (start_n + offs_n[:, None]) * stride_kn
        K_ptrs = K_ptr + k_offset + offs_d[None, :] * stride_kd
        
        v_offset = v_offset_base + (start_n + offs_n[:, None]) * stride_vn
        V_ptrs = V_ptr + v_offset + offs_d[None, :] * stride_vd
        
        q = tl.load(Q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dq), other=0.0)
        k = tl.load(K_ptrs, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dq), other=0.0)
        v = tl.load(V_ptrs, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dv), other=0.0)
        
        q = q.to(tl.float32)
        k = k.to(tl.float32)
        v = v.to(tl.float32)
        
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        m_ij = tl.max(s, 1)
        p = tl.exp(s - m_ij[:, None])
        
        l_ij = tl.sum(p, 1)
        acc_scale = tl.exp(m_i - m_ij)
        
        acc = acc * acc_scale[:, None]
        acc += tl.dot(p.to(v.dtype), v)
        
        m_i = tl.maximum(m_i, m_ij)
        l_i = l_i * acc_scale + l_ij
    
    acc = acc / l_i[:, None]
    acc = acc.to(tl.float16)
    
    out_offset = pid_batch * stride_oz + pid_head * stride_oh + offs_m[:, None] * stride_om
    Out_ptrs = Out_ptr + out_offset + offs_d[None, :] * stride_od
    
    tl.store(Out_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = lambda META: (
        Z,
        H,
        triton.cdiv(M, META['BLOCK_M']),
    )
    
    _decoding_attn_fwd_kernel[grid](
        Q, K, V, out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale=scale,
    )
    
    return out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 128, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 128, 'num_warps': 8}),
    ],
    key=['M', 'N', 'Dq'],
)
@triton.jit
def _decoding_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_offset = pid_batch * stride_qz + pid_head * stride_qh + offs_m[:, None] * stride_qm
    Q_ptrs = Q_ptr + q_offset + offs_d[None, :] * stride_qd
    
    k_offset_base = pid_batch * stride_kz + pid_head * stride_kh
    v_offset_base = pid_batch * stride_vz + pid_head * stride_vh
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        k_offset = k_offset_base + (start_n + offs_n[:, None]) * stride_kn
        K_ptrs = K_ptr + k_offset + offs_d[None, :] * stride_kd
        
        v_offset = v_offset_base + (start_n + offs_n[:, None]) * stride_vn
        V_ptrs = V_ptr + v_offset + offs_d[None, :] * stride_vd
        
        q = tl.load(Q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dq), other=0.0)
        k = tl.load(K_ptrs, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dq), other=0.0)
        v = tl.load(V_ptrs, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dv), other=0.0)
        
        q = q.to(tl.float32)
        k = k.to(tl.float32)
        v = v.to(tl.float32)
        
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        m_ij = tl.max(s, 1)
        p = tl.exp(s - m_ij[:, None])
        
        l_ij = tl.sum(p, 1)
        acc_scale = tl.exp(m_i - m_ij)
        
        acc = acc * acc_scale[:, None]
        acc += tl.dot(p.to(v.dtype), v)
        
        m_i = tl.maximum(m_i, m_ij)
        l_i = l_i * acc_scale + l_ij
    
    acc = acc / l_i[:, None]
    acc = acc.to(tl.float16)
    
    out_offset = pid_batch * stride_oz + pid_head * stride_oh + offs_m[:, None] * stride_om
    Out_ptrs = Out_ptr + out_offset + offs_d[None, :] * stride_od
    
    tl.store(Out_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = lambda META: (
        Z,
        H,
        triton.cdiv(M, META['BLOCK_M']),
    )
    
    _decoding_attn_fwd_kernel[grid](
        Q, K, V, out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale=scale,
    )
    
    return out'''
        
        return {"code": code}