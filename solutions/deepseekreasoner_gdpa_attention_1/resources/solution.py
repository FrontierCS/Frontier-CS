import torch
import triton
import triton.language as tl
from typing import Optional
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Create block pointers for loading Q and GQ
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_D)
    
    Q_block_ptr = tl.make_block_ptr(
        base=Q_ptr + pid_z * stride_qz + pid_h * stride_qh,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    GQ_block_ptr = tl.make_block_ptr(
        base=GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh,
        shape=(M, Dq),
        strides=(stride_gqm, stride_gqd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    # Initialize accumulators
    acc = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Loop over N dimension in blocks
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        # Load K and GK blocks
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        K_block_ptr = tl.make_block_ptr(
            base=K_ptr + pid_z * stride_kz + pid_h * stride_kh,
            shape=(N, Dq),
            strides=(stride_kn, stride_kd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        GK_block_ptr = tl.make_block_ptr(
            base=GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh,
            shape=(N, Dq),
            strides=(stride_gkn, stride_gkd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        # Load blocks
        Q_block = tl.load(Q_block_ptr, boundary_check=(0, 1))
        GQ_block = tl.load(GQ_block_ptr, boundary_check=(0, 1))
        K_block = tl.load(K_block_ptr, boundary_check=(0, 1))
        GK_block = tl.load(GK_block_ptr, boundary_check=(0, 1))
        
        # Apply gating: sigmoid(gate) * tensor
        Qg = Q_block * tl.sigmoid(GQ_block)
        Kg = K_block * tl.sigmoid(GK_block)
        
        # Compute attention scores
        S = tl.dot(Qg, tl.trans(Kg))
        S = S * scale
        
        # Load V block
        V_block_ptr = tl.make_block_ptr(
            base=V_ptr + pid_z * stride_vz + pid_h * stride_vh,
            shape=(N, Dv),
            strides=(stride_vn, stride_vd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        V_block = tl.load(V_block_ptr, boundary_check=(0, 1))
        
        # Compute softmax with numerical stability
        m_ij = tl.max(S, axis=1)
        p = tl.exp(S - m_ij[:, None])
        l_ij = tl.sum(p, axis=1)
        
        # Update softmax statistics
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(m_ij - m_i_new)
        l_i_new = alpha * l_i + beta * l_ij
        
        # Scale current acc by alpha and add new contributions
        acc = acc * alpha[:, None]
        pV = tl.dot(p.to(tl.float16), V_block.to(tl.float16))
        acc = acc + beta[:, None] * pV.to(tl.float32)
        
        # Update statistics for next iteration
        m_i = m_i_new
        l_i = l_i_new
    
    # Normalize and write output
    acc = acc / l_i[:, None]
    
    # Create output block pointer
    Out_block_ptr = tl.make_block_ptr(
        base=Out_ptr + pid_z * stride_oz + pid_h * stride_oh,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    tl.store(Out_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert GQ.dtype == torch.float16
    assert GK.dtype == torch.float16
    
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    scale = 1.0 / math.sqrt(Dq)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=64, BLOCK_N=64, BLOCK_D=64
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl
from typing import Optional
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Create block pointers for loading Q and GQ
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_D)
    
    Q_block_ptr = tl.make_block_ptr(
        base=Q_ptr + pid_z * stride_qz + pid_h * stride_qh,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    GQ_block_ptr = tl.make_block_ptr(
        base=GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh,
        shape=(M, Dq),
        strides=(stride_gqm, stride_gqd),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    # Initialize accumulators
    acc = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Loop over N dimension in blocks
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        # Load K and GK blocks
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        K_block_ptr = tl.make_block_ptr(
            base=K_ptr + pid_z * stride_kz + pid_h * stride_kh,
            shape=(N, Dq),
            strides=(stride_kn, stride_kd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        GK_block_ptr = tl.make_block_ptr(
            base=GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh,
            shape=(N, Dq),
            strides=(stride_gkn, stride_gkd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        # Load blocks
        Q_block = tl.load(Q_block_ptr, boundary_check=(0, 1))
        GQ_block = tl.load(GQ_block_ptr, boundary_check=(0, 1))
        K_block = tl.load(K_block_ptr, boundary_check=(0, 1))
        GK_block = tl.load(GK_block_ptr, boundary_check=(0, 1))
        
        # Apply gating: sigmoid(gate) * tensor
        Qg = Q_block * tl.sigmoid(GQ_block)
        Kg = K_block * tl.sigmoid(GK_block)
        
        # Compute attention scores
        S = tl.dot(Qg, tl.trans(Kg))
        S = S * scale
        
        # Load V block
        V_block_ptr = tl.make_block_ptr(
            base=V_ptr + pid_z * stride_vz + pid_h * stride_vh,
            shape=(N, Dv),
            strides=(stride_vn, stride_vd),
            offsets=(start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        V_block = tl.load(V_block_ptr, boundary_check=(0, 1))
        
        # Compute softmax with numerical stability
        m_ij = tl.max(S, axis=1)
        p = tl.exp(S - m_ij[:, None])
        l_ij = tl.sum(p, axis=1)
        
        # Update softmax statistics
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(m_ij - m_i_new)
        l_i_new = alpha * l_i + beta * l_ij
        
        # Scale current acc by alpha and add new contributions
        acc = acc * alpha[:, None]
        pV = tl.dot(p.to(tl.float16), V_block.to(tl.float16))
        acc = acc + beta[:, None] * pV.to(tl.float32)
        
        # Update statistics for next iteration
        m_i = m_i_new
        l_i = l_i_new
    
    # Normalize and write output
    acc = acc / l_i[:, None]
    
    # Create output block pointer
    Out_block_ptr = tl.make_block_ptr(
        base=Out_ptr + pid_z * stride_oz + pid_h * stride_oh,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    tl.store(Out_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert GQ.dtype == torch.float16
    assert GK.dtype == torch.float16
    
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    scale = 1.0 / math.sqrt(Dq)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=64, BLOCK_N=64, BLOCK_D=64
    )
    
    return Out
"""
        return {"code": code}
