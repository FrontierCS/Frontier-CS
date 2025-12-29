import torch
import triton
import triton.language as tl
import math
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=2),
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
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_z = pid_batch
    offs_h = pid_head
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    q_ptrs = Q_ptr + offs_z * stride_qz + offs_h * stride_qh + offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qd
    k_ptrs = K_ptr + offs_z * stride_kz + offs_h * stride_kh + offs_n[None, :] * stride_kn + offs_k[:, None] * stride_kd
    v_ptrs = V_ptr + offs_z * stride_vz + offs_h * stride_vh + offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :] * stride_vd
    
    acc = tl.zeros((BLOCK_SIZE_M, Dv), dtype=tl.float32)
    max_logits = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    norm = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    n_blocks = tl.cdiv(N, BLOCK_SIZE_N)
    
    for block_n in range(0, n_blocks):
        n_start = block_n * BLOCK_SIZE_N
        n_end = n_start + BLOCK_SIZE_N
        
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        
        offs_n_current = n_start + offs_n
        k_mask = offs_n_current[None, :] < N
        k = tl.load(k_ptrs + n_start * stride_kn, mask=k_mask & (offs_k[:, None] < Dq), other=0.0)
        
        s = tl.dot(q, k) * scale
        s = tl.where(offs_m[:, None] < M, s, float('-inf'))
        
        m_new = tl.maximum(max_logits, tl.max(s, axis=1))
        s = tl.exp(s - m_new[:, None])
        
        v_mask = offs_n_current[:, None] < N
        v = tl.load(v_ptrs + n_start * stride_vn, mask=v_mask, other=0.0)
        
        p = s
        acc = acc * tl.exp(max_logits - m_new)[:, None] + tl.dot(p, v)
        norm = norm * tl.exp(max_logits - m_new) + tl.sum(p, axis=1)
        max_logits = m_new
        
    acc = acc / norm[:, None]
    
    out_ptrs = Out_ptr + offs_z * stride_oz + offs_h * stride_oh + offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * stride_od
    out_mask = offs_m[:, None] < M
    tl.store(out_ptrs, acc.to(tl.float16), mask=out_mask)

def decoding_attn(
    Q: torch.Tensor,
    K: torch.Tensor, 
    V: torch.Tensor,
    causal: bool = False,
    scale: Optional[float] = None
) -> torch.Tensor:
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    if scale is None:
        scale = 1.0 / math.sqrt(Dq)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 128))
    
    _decoding_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl
import math
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=5, num_warps=2),
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
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_z = pid_batch
    offs_h = pid_head
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    q_ptrs = Q_ptr + offs_z * stride_qz + offs_h * stride_qh + offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qd
    k_ptrs = K_ptr + offs_z * stride_kz + offs_h * stride_kh + offs_n[None, :] * stride_kn + offs_k[:, None] * stride_kd
    v_ptrs = V_ptr + offs_z * stride_vz + offs_h * stride_vh + offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :] * stride_vd
    
    acc = tl.zeros((BLOCK_SIZE_M, Dv), dtype=tl.float32)
    max_logits = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    norm = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    n_blocks = tl.cdiv(N, BLOCK_SIZE_N)
    
    for block_n in range(0, n_blocks):
        n_start = block_n * BLOCK_SIZE_N
        n_end = n_start + BLOCK_SIZE_N
        
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        
        offs_n_current = n_start + offs_n
        k_mask = offs_n_current[None, :] < N
        k = tl.load(k_ptrs + n_start * stride_kn, mask=k_mask & (offs_k[:, None] < Dq), other=0.0)
        
        s = tl.dot(q, k) * scale
        s = tl.where(offs_m[:, None] < M, s, float('-inf'))
        
        m_new = tl.maximum(max_logits, tl.max(s, axis=1))
        s = tl.exp(s - m_new[:, None])
        
        v_mask = offs_n_current[:, None] < N
        v = tl.load(v_ptrs + n_start * stride_vn, mask=v_mask, other=0.0)
        
        p = s
        acc = acc * tl.exp(max_logits - m_new)[:, None] + tl.dot(p, v)
        norm = norm * tl.exp(max_logits - m_new) + tl.sum(p, axis=1)
        max_logits = m_new
        
    acc = acc / norm[:, None]
    
    out_ptrs = Out_ptr + offs_z * stride_oz + offs_h * stride_oh + offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * stride_od
    out_mask = offs_m[:, None] < M
    tl.store(out_ptrs, acc.to(tl.float16), mask=out_mask)

def decoding_attn(
    Q: torch.Tensor,
    K: torch.Tensor, 
    V: torch.Tensor,
    causal: bool = False,
    scale: Optional[float] = None
) -> torch.Tensor:
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    if scale is None:
        scale = 1.0 / math.sqrt(Dq)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 128))
    
    _decoding_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
    )
    
    return Out"""
        
        return {"code": code}