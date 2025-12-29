import torch
import triton
import triton.language as tl
from typing import Optional, Tuple
import os


@triton.jit
def _gdpa_kernel(
    # Pointers to tensors
    Q_ptr,
    K_ptr,
    V_ptr,
    GQ_ptr,
    GK_ptr,
    Out_ptr,
    # Tensor dimensions
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    # Strides
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_gqz,
    stride_gqh,
    stride_gqm,
    stride_gqd,
    stride_gkz,
    stride_gkh,
    stride_gkn,
    stride_gkd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    USE_TMA: tl.constexpr = False,
):
    """Triton kernel for GDPA attention with gating."""
    
    # -----------------------------------------------------------
    # Program ID and offsets
    # -----------------------------------------------------------
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets for this block
    m_start = pid_m * BLOCK_M
    m_offsets = m_start + tl.arange(0, BLOCK_M)
    n_offsets = tl.arange(0, BLOCK_N)
    dq_offsets = tl.arange(0, BLOCK_Dq)
    dv_offsets = tl.arange(0, BLOCK_Dv)
    
    # -----------------------------------------------------------
    # Create block pointers for efficient memory access
    # -----------------------------------------------------------
    # Q block pointer (BLOCK_M x BLOCK_Dq)
    if USE_TMA:
        q_block_ptr = tl.make_block_ptr(
            base=Q_ptr + pid_batch * stride_qz + pid_head * stride_qh,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(m_start, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
    else:
        q_ptrs = Q_ptr + pid_batch * stride_qz + pid_head * stride_qh + \
                m_offsets[:, None] * stride_qm + dq_offsets[None, :] * stride_qd
    
    # GQ block pointer
    if USE_TMA:
        gq_block_ptr = tl.make_block_ptr(
            base=GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh,
            shape=(M, Dq),
            strides=(stride_gqm, stride_gqd),
            offsets=(m_start, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
    else:
        gq_ptrs = GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh + \
                 m_offsets[:, None] * stride_gqm + dq_offsets[None, :] * stride_gqd
    
    # Initialize accumulators for output (BLOCK_M x BLOCK_Dv)
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)
    
    # Initialize max and sum for softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Load and compute gated Q for this block
    # -----------------------------------------------------------
    if USE_TMA:
        q_block = tl.load(q_block_ptr, boundary_check=(0, 1), padding_option='zero')
        gq_block = tl.load(gq_block_ptr, boundary_check=(0, 1), padding_option='zero')
    else:
        mask_q = (m_offsets[:, None] < M) & (dq_offsets[None, :] < Dq)
        q_block = tl.load(q_ptrs, mask=mask_q, other=0.0)
        gq_block = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    
    # Apply sigmoid gate to Q
    q_gated = q_block * tl.sigmoid(gq_block)
    
    # Scale factor
    scale = 1.0 / tl.sqrt(tl.float32(Dq))
    
    # -----------------------------------------------------------
    # Loop over N dimension in blocks
    # -----------------------------------------------------------
    for n_start in range(0, N, BLOCK_N):
        n_start_idx = n_start
        n_offsets_current = n_start_idx + n_offsets
        
        # Create block pointers for K, GK, V
        if USE_TMA:
            # K block pointer
            k_block_ptr = tl.make_block_ptr(
                base=K_ptr + pid_batch * stride_kz + pid_head * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(n_start_idx, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            
            # GK block pointer
            gk_block_ptr = tl.make_block_ptr(
                base=GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkd),
                offsets=(n_start_idx, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            
            # V block pointer
            v_block_ptr = tl.make_block_ptr(
                base=V_ptr + pid_batch * stride_vz + pid_head * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(n_start_idx, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            
            k_block = tl.load(k_block_ptr, boundary_check=(0, 1), padding_option='zero')
            gk_block = tl.load(gk_block_ptr, boundary_check=(0, 1), padding_option='zero')
            v_block = tl.load(v_block_ptr, boundary_check=(0, 1), padding_option='zero')
        else:
            # Regular pointer arithmetic
            k_ptrs = K_ptr + pid_batch * stride_kz + pid_head * stride_kh + \
                    n_offsets_current[None, :] * stride_kn + dq_offsets[:, None] * stride_kd
            
            gk_ptrs = GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh + \
                     n_offsets_current[None, :] * stride_gkn + dq_offsets[:, None] * stride_gkd
            
            v_ptrs = V_ptr + pid_batch * stride_vz + pid_head * stride_vh + \
                    n_offsets_current[:, None] * stride_vn + dv_offsets[None, :] * stride_vd
            
            # Masks for boundaries
            mask_k = (n_offsets_current[None, :] < N) & (dq_offsets[:, None] < Dq)
            mask_v = (n_offsets_current[:, None] < N) & (dv_offsets[None, :] < Dv)
            
            k_block = tl.load(k_ptrs, mask=mask_k, other=0.0)
            gk_block = tl.load(gk_ptrs, mask=mask_k, other=0.0)
            v_block = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Apply sigmoid gate to K and transpose
        k_gated = k_block * tl.sigmoid(gk_block)
        k_gated_t = tl.trans(k_gated)
        
        # -------------------------------------------------------
        # Compute attention scores (BLOCK_M x BLOCK_N)
        # -------------------------------------------------------
        scores = tl.dot(q_gated, k_gated_t) * scale
        
        # -------------------------------------------------------
        # Streaming softmax update
        # -------------------------------------------------------
        # Find new max for each row
        n_mask = n_offsets_current < N
        scores_masked = tl.where(n_mask[None, :], scores, float('-inf'))
        m_ij = tl.max(scores_masked, axis=1)
        
        # Compute exponentials
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        # Update sum for softmax denominator
        exp_scores = tl.exp(scores_masked - m_new[:, None])
        l_ij = tl.sum(exp_scores, axis=1)
        l_new = alpha * l_i + beta * l_ij
        
        # Update accumulators
        acc_scale = l_i / (l_new + 1e-6)
        acc = acc * alpha[:, None] * acc_scale[:, None]
        
        # Add new contribution
        p = exp_scores / (l_new[:, None] + 1e-6)
        acc += tl.dot(p, v_block)
        
        # Update m_i and l_i
        m_i = m_new
        l_i = l_new
    
    # -----------------------------------------------------------
    # Store output
    # -----------------------------------------------------------
    if USE_TMA:
        out_block_ptr = tl.make_block_ptr(
            base=Out_ptr + pid_batch * stride_oz + pid_head * stride_oh,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(m_start, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
        tl.store(out_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))
    else:
        out_ptrs = Out_ptr + pid_batch * stride_oz + pid_head * stride_oh + \
                  m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_od
        mask_out = (m_offsets[:, None] < M) & (dv_offsets[None, :] < Dv)
        tl.store(out_ptrs, acc.to(tl.float16), mask=mask_out)


@triton.jit
def _gdpa_kernel_optimized(
    # Pointers to tensors
    Q_ptr,
    K_ptr,
    V_ptr,
    GQ_ptr,
    GK_ptr,
    Out_ptr,
    # Tensor dimensions
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    # Strides
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_gqz,
    stride_gqh,
    stride_gqm,
    stride_gqd,
    stride_gkz,
    stride_gkh,
    stride_gkn,
    stride_gkd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
):
    """Optimized GDPA kernel with better cache utilization."""
    
    # Program IDs
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets
    m_start = pid_m * BLOCK_M
    m_offsets = m_start + tl.arange(0, BLOCK_M)
    n_offsets = tl.arange(0, BLOCK_N)
    dq_offsets = tl.arange(0, BLOCK_Dq)
    dv_offsets = tl.arange(0, BLOCK_Dv)
    
    # -----------------------------------------------------------
    # Load Q and GQ for this block with masking
    # -----------------------------------------------------------
    q_ptrs = Q_ptr + pid_batch * stride_qz + pid_head * stride_qh + \
            m_offsets[:, None] * stride_qm + dq_offsets[None, :] * stride_qd
    
    gq_ptrs = GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh + \
             m_offsets[:, None] * stride_gqm + dq_offsets[None, :] * stride_gqd
    
    mask_q = (m_offsets[:, None] < M) & (dq_offsets[None, :] < Dq)
    q_block = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq_block = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    
    # Apply gating
    q_gated = q_block * tl.sigmoid(gq_block)
    
    # Scale factor
    scale = 1.0 / tl.sqrt(tl.float32(Dq))
    
    # Initialize accumulators
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Main loop over N dimension
    # -----------------------------------------------------------
    for n_start in range(0, N, BLOCK_N):
        n_offsets_cur = n_start + n_offsets
        
        # Load K, GK, V for current block
        k_ptrs = K_ptr + pid_batch * stride_kz + pid_head * stride_kh + \
                n_offsets_cur[None, :] * stride_kn + dq_offsets[:, None] * stride_kd
        
        gk_ptrs = GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh + \
                 n_offsets_cur[None, :] * stride_gkn + dq_offsets[:, None] * stride_gkd
        
        v_ptrs = V_ptr + pid_batch * stride_vz + pid_head * stride_vh + \
                n_offsets_cur[:, None] * stride_vn + dv_offsets[None, :] * stride_vd
        
        mask_k = (n_offsets_cur[None, :] < N) & (dq_offsets[:, None] < Dq)
        mask_v = (n_offsets_cur[:, None] < N) & (dv_offsets[None, :] < Dv)
        
        k_block = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk_block = tl.load(gk_ptrs, mask=mask_k, other=0.0)
        v_block = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Apply gating to K
        k_gated = k_block * tl.sigmoid(gk_block)
        
        # Compute attention scores
        scores = tl.dot(q_gated, tl.trans(k_gated)) * scale
        
        # Apply mask for N boundary
        n_mask = n_offsets_cur < N
        scores_masked = tl.where(n_mask[None, :], scores, float('-inf'))
        
        # Streaming softmax
        m_ij = tl.max(scores_masked, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        exp_scores = tl.exp(scores_masked - m_new[:, None])
        l_ij = tl.sum(exp_scores, axis=1)
        l_new = alpha * l_i + beta * l_ij
        
        # Update accumulator
        if n_start > 0:
            acc = acc * alpha[:, None] * (l_i / (l_new + 1e-6))[:, None]
        
        # Add new contribution
        p = exp_scores / (l_new[:, None] + 1e-6)
        acc += tl.dot(p, v_block)
        
        # Update running stats
        m_i = m_new
        l_i = l_new
    
    # -----------------------------------------------------------
    # Store output
    # -----------------------------------------------------------
    out_ptrs = Out_ptr + pid_batch * stride_oz + pid_head * stride_oh + \
              m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_od
    
    mask_out = (m_offsets[:, None] < M) & (dv_offsets[None, :] < Dv)
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_out)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        GQ: Input tensor of shape (Z, H, M, Dq) - query gate tensor (float16)
        GK: Input tensor of shape (Z, H, N, Dq) - key gate tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Check dimensions
    assert K.shape == (Z, H, N, Dq), f"K shape {K.shape} != {(Z, H, N, Dq)}"
    assert V.shape == (Z, H, N, Dv), f"V shape {V.shape} != {(Z, H, N, Dv)}"
    assert GQ.shape == (Z, H, M, Dq), f"GQ shape {GQ.shape} != {(Z, H, M, Dq)}"
    assert GK.shape == (Z, H, N, Dq), f"GK shape {GK.shape} != {(Z, H, N, Dq)}"
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)
    
    # Choose optimal block sizes based on sequence length
    if M <= 512:
        BLOCK_M = 64
        BLOCK_N = 64
    elif M <= 1024:
        BLOCK_M = 64
        BLOCK_N = 128
    else:
        BLOCK_M = 64
        BLOCK_N = 256
    
    # Ensure block sizes don't exceed dimensions
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    # Compute grid
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    # Launch kernel
    _gdpa_kernel_optimized[grid](
        Q, K, V, GQ, GK, Out,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """Returns the solution code."""
        code = '''"""GDPA Attention Implementation with Triton Optimizations"""
import torch
import triton
import triton.language as tl
from typing import Optional, Tuple
import os


@triton.jit
def _gdpa_kernel(
    # Pointers to tensors
    Q_ptr,
    K_ptr,
    V_ptr,
    GQ_ptr,
    GK_ptr,
    Out_ptr,
    # Tensor dimensions
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    # Strides
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_gqz,
    stride_gqh,
    stride_gqm,
    stride_gqd,
    stride_gkz,
    stride_gkh,
    stride_gkn,
    stride_gkd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    USE_TMA: tl.constexpr = False,
):
    """Triton kernel for GDPA attention with gating."""
    
    # -----------------------------------------------------------
    # Program ID and offsets
    # -----------------------------------------------------------
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets for this block
    m_start = pid_m * BLOCK_M
    m_offsets = m_start + tl.arange(0, BLOCK_M)
    n_offsets = tl.arange(0, BLOCK_N)
    dq_offsets = tl.arange(0, BLOCK_Dq)
    dv_offsets = tl.arange(0, BLOCK_Dv)
    
    # -----------------------------------------------------------
    # Create block pointers for efficient memory access
    # -----------------------------------------------------------
    # Q block pointer (BLOCK_M x BLOCK_Dq)
    if USE_TMA:
        q_block_ptr = tl.make_block_ptr(
            base=Q_ptr + pid_batch * stride_qz + pid_head * stride_qh,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(m_start, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
    else:
        q_ptrs = Q_ptr + pid_batch * stride_qz + pid_head * stride_qh + \
                m_offsets[:, None] * stride_qm + dq_offsets[None, :] * stride_qd
    
    # GQ block pointer
    if USE_TMA:
        gq_block_ptr = tl.make_block_ptr(
            base=GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh,
            shape=(M, Dq),
            strides=(stride_gqm, stride_gqd),
            offsets=(m_start, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
    else:
        gq_ptrs = GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh + \
                 m_offsets[:, None] * stride_gqm + dq_offsets[None, :] * stride_gqd
    
    # Initialize accumulators for output (BLOCK_M x BLOCK_Dv)
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)
    
    # Initialize max and sum for softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Load and compute gated Q for this block
    # -----------------------------------------------------------
    if USE_TMA:
        q_block = tl.load(q_block_ptr, boundary_check=(0, 1), padding_option='zero')
        gq_block = tl.load(gq_block_ptr, boundary_check=(0, 1), padding_option='zero')
    else:
        mask_q = (m_offsets[:, None] < M) & (dq_offsets[None, :] < Dq)
        q_block = tl.load(q_ptrs, mask=mask_q, other=0.0)
        gq_block = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    
    # Apply sigmoid gate to Q
    q_gated = q_block * tl.sigmoid(gq_block)
    
    # Scale factor
    scale = 1.0 / tl.sqrt(tl.float32(Dq))
    
    # -----------------------------------------------------------
    # Loop over N dimension in blocks
    # -----------------------------------------------------------
    for n_start in range(0, N, BLOCK_N):
        n_start_idx = n_start
        n_offsets_current = n_start_idx + n_offsets
        
        # Create block pointers for K, GK, V
        if USE_TMA:
            # K block pointer
            k_block_ptr = tl.make_block_ptr(
                base=K_ptr + pid_batch * stride_kz + pid_head * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(n_start_idx, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            
            # GK block pointer
            gk_block_ptr = tl.make_block_ptr(
                base=GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkd),
                offsets=(n_start_idx, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            
            # V block pointer
            v_block_ptr = tl.make_block_ptr(
                base=V_ptr + pid_batch * stride_vz + pid_head * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(n_start_idx, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            
            k_block = tl.load(k_block_ptr, boundary_check=(0, 1), padding_option='zero')
            gk_block = tl.load(gk_block_ptr, boundary_check=(0, 1), padding_option='zero')
            v_block = tl.load(v_block_ptr, boundary_check=(0, 1), padding_option='zero')
        else:
            # Regular pointer arithmetic
            k_ptrs = K_ptr + pid_batch * stride_kz + pid_head * stride_kh + \
                    n_offsets_current[None, :] * stride_kn + dq_offsets[:, None] * stride_kd
            
            gk_ptrs = GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh + \
                     n_offsets_current[None, :] * stride_gkn + dq_offsets[:, None] * stride_gkd
            
            v_ptrs = V_ptr + pid_batch * stride_vz + pid_head * stride_vh + \
                    n_offsets_current[:, None] * stride_vn + dv_offsets[None, :] * stride_vd
            
            # Masks for boundaries
            mask_k = (n_offsets_current[None, :] < N) & (dq_offsets[:, None] < Dq)
            mask_v = (n_offsets_current[:, None] < N) & (dv_offsets[None, :] < Dv)
            
            k_block = tl.load(k_ptrs, mask=mask_k, other=0.0)
            gk_block = tl.load(gk_ptrs, mask=mask_k, other=0.0)
            v_block = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Apply sigmoid gate to K and transpose
        k_gated = k_block * tl.sigmoid(gk_block)
        k_gated_t = tl.trans(k_gated)
        
        # -------------------------------------------------------
        # Compute attention scores (BLOCK_M x BLOCK_N)
        # -------------------------------------------------------
        scores = tl.dot(q_gated, k_gated_t) * scale
        
        # -------------------------------------------------------
        # Streaming softmax update
        # -------------------------------------------------------
        # Find new max for each row
        n_mask = n_offsets_current < N
        scores_masked = tl.where(n_mask[None, :], scores, float('-inf'))
        m_ij = tl.max(scores_masked, axis=1)
        
        # Compute exponentials
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        # Update sum for softmax denominator
        exp_scores = tl.exp(scores_masked - m_new[:, None])
        l_ij = tl.sum(exp_scores, axis=1)
        l_new = alpha * l_i + beta * l_ij
        
        # Update accumulators
        acc_scale = l_i / (l_new + 1e-6)
        acc = acc * alpha[:, None] * acc_scale[:, None]
        
        # Add new contribution
        p = exp_scores / (l_new[:, None] + 1e-6)
        acc += tl.dot(p, v_block)
        
        # Update m_i and l_i
        m_i = m_new
        l_i = l_new
    
    # -----------------------------------------------------------
    # Store output
    # -----------------------------------------------------------
    if USE_TMA:
        out_block_ptr = tl.make_block_ptr(
            base=Out_ptr + pid_batch * stride_oz + pid_head * stride_oh,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(m_start, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
        tl.store(out_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))
    else:
        out_ptrs = Out_ptr + pid_batch * stride_oz + pid_head * stride_oh + \
                  m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_od
        mask_out = (m_offsets[:, None] < M) & (dv_offsets[None, :] < Dv)
        tl.store(out_ptrs, acc.to(tl.float16), mask=mask_out)


@triton.jit
def _gdpa_kernel_optimized(
    # Pointers to tensors
    Q_ptr,
    K_ptr,
    V_ptr,
    GQ_ptr,
    GK_ptr,
    Out_ptr,
    # Tensor dimensions
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    # Strides
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_gqz,
    stride_gqh,
    stride_gqm,
    stride_gqd,
    stride_gkz,
    stride_gkh,
    stride_gkn,
    stride_gkd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
):
    """Optimized GDPA kernel with better cache utilization."""
    
    # Program IDs
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets
    m_start = pid_m * BLOCK_M
    m_offsets = m_start + tl.arange(0, BLOCK_M)
    n_offsets = tl.arange(0, BLOCK_N)
    dq_offsets = tl.arange(0, BLOCK_Dq)
    dv_offsets = tl.arange(0, BLOCK_Dv)
    
    # -----------------------------------------------------------
    # Load Q and GQ for this block with masking
    # -----------------------------------------------------------
    q_ptrs = Q_ptr + pid_batch * stride_qz + pid_head * stride_qh + \
            m_offsets[:, None] * stride_qm + dq_offsets[None, :] * stride_qd
    
    gq_ptrs = GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh + \
             m_offsets[:, None] * stride_gqm + dq_offsets[None, :] * stride_gqd
    
    mask_q = (m_offsets[:, None] < M) & (dq_offsets[None, :] < Dq)
    q_block = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq_block = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    
    # Apply gating
    q_gated = q_block * tl.sigmoid(gq_block)
    
    # Scale factor
    scale = 1.0 / tl.sqrt(tl.float32(Dq))
    
    # Initialize accumulators
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Main loop over N dimension
    # -----------------------------------------------------------
    for n_start in range(0, N, BLOCK_N):
        n_offsets_cur = n_start + n_offsets
        
        # Load K, GK, V for current block
        k_ptrs = K_ptr + pid_batch * stride_kz + pid_head * stride_kh + \
                n_offsets_cur[None, :] * stride_kn + dq_offsets[:, None] * stride_kd
        
        gk_ptrs = GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh + \
                 n_offsets_cur[None, :] * stride_gkn + dq_offsets[:, None] * stride_gkd
        
        v_ptrs = V_ptr + pid_batch * stride_vz + pid_head * stride_vh + \
                n_offsets_cur[:, None] * stride_vn + dv_offsets[None, :] * stride_vd
        
        mask_k = (n_offsets_cur[None, :] < N) & (dq_offsets[:, None] < Dq)
        mask_v = (n_offsets_cur[:, None] < N) & (dv_offsets[None, :] < Dv)
        
        k_block = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk_block = tl.load(gk_ptrs, mask=mask_k, other=0.0)
        v_block = tl.load(v_ptrs, mask=mask_v, other=0.0)
        
        # Apply gating to K
        k_gated = k_block * tl.sigmoid(gk_block)
        
        # Compute attention scores
        scores = tl.dot(q_gated, tl.trans(k_gated)) * scale
        
        # Apply mask for N boundary
        n_mask = n_offsets_cur < N
        scores_masked = tl.where(n_mask[None, :], scores, float('-inf'))
        
        # Streaming softmax
        m_ij = tl.max(scores_masked, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        exp_scores = tl.exp(scores_masked - m_new[:, None])
        l_ij = tl.sum(exp_scores, axis=1)
        l_new = alpha * l_i + beta * l_ij
        
        # Update accumulator
        if n_start > 0:
            acc = acc * alpha[:, None] * (l_i / (l_new + 1e-6))[:, None]
        
        # Add new contribution
        p = exp_scores / (l_new[:, None] + 1e-6)
        acc += tl.dot(p, v_block)
        
        # Update running stats
        m_i = m_new
        l_i = l_new
    
    # -----------------------------------------------------------
    # Store output
    # -----------------------------------------------------------
    out_ptrs = Out_ptr + pid_batch * stride_oz + pid_head * stride_oh + \
              m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_od
    
    mask_out = (m_offsets[:, None] < M) & (dv_offsets[None, :] < Dv)
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_out)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        GQ: Input tensor of shape (Z, H, M, Dq) - query gate tensor (float16)
        GK: Input tensor of shape (Z, H, N, Dq) - key gate tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Check dimensions
    assert K.shape == (Z, H, N, Dq), f"K shape {K.shape} != {(Z, H, N, Dq)}"
    assert V.shape == (Z, H, N, Dv), f"V shape {V.shape} != {(Z, H, N, Dv)}"
    assert GQ.shape == (Z, H, M, Dq), f"GQ shape {GQ.shape} != {(Z, H, M, Dq)}"
    assert GK.shape == (Z, H, N, Dq), f"GK shape {GK.shape} != {(Z, H, N, Dq)}"
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)
    
    # Choose optimal block sizes based on sequence length
    if M <= 512:
        BLOCK_M = 64
        BLOCK_N = 64
    elif M <= 1024:
        BLOCK_M = 64
        BLOCK_N = 128
    else:
        BLOCK_M = 64
        BLOCK_N = 256
    
    # Ensure block sizes don't exceed dimensions
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    # Compute grid
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    # Launch kernel
    _gdpa_kernel_optimized[grid](
        Q, K, V, GQ, GK, Out,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv
    )
    
    return Out
'''
        return {"code": code}