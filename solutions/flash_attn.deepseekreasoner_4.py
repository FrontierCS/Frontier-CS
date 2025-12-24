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
    CAUSAL: tl.constexpr,
    IS_TRAINING: tl.constexpr
):
    # -----------------------------------------------------------
    # Program ID
    pid_z = tl.program_id(0)  # batch
    pid_h = tl.program_id(1)  # head
    pid_m = tl.program_id(2)  # query block idx

    # -----------------------------------------------------------
    # Create block pointers for Q
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    q_ptrs = Q + q_offset + (pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] * stride_qm + tl.arange(0, BLOCK_D)[None, :] * stride_qd
    
    # -----------------------------------------------------------
    # Initialize pointers to K, V
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    
    # -----------------------------------------------------------
    # Initialize accumulator and stats
    o = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Load Q block
    q = tl.load(q_ptrs, mask=(pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] < M, other=0.0)
    q = q.to(tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq)
    q = q * scale
    
    # -----------------------------------------------------------
    # Loop over K, V blocks
    lo = 0
    hi = N
    for block_n in range(lo, hi, BLOCK_N):
        # -------------------------------------------------------
        # Compute K block pointer and load K
        k_ptrs = K + k_offset + (block_n + tl.arange(0, BLOCK_N))[:, None] * stride_kn + tl.arange(0, BLOCK_D)[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=(block_n + tl.arange(0, BLOCK_N))[:, None] < N, other=0.0)
        k = k.to(tl.float32)
        
        # -------------------------------------------------------
        # Compute QK^T
        s = tl.dot(q, tl.trans(k))
        
        # -------------------------------------------------------
        # Apply causal masking if needed
        if CAUSAL:
            q_idx = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            k_idx = block_n + tl.arange(0, BLOCK_N)
            mask = q_idx[:, None] >= k_idx[None, :]
            s = tl.where(mask, s, float('-inf'))
        
        # -------------------------------------------------------
        # Compute statistics for this block
        m_ij = tl.max(s, axis=1)
        p = tl.exp(s - m_ij[:, None])
        
        # -------------------------------------------------------
        # Update accumulator and stats
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_i = l_i * alpha + tl.sum(p * beta[:, None], axis=1)
        
        # Load V block
        v_ptrs = V + v_offset + (block_n + tl.arange(0, BLOCK_N))[:, None] * stride_vn + tl.arange(0, BLOCK_D)[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=(block_n + tl.arange(0, BLOCK_N))[:, None] < N, other=0.0)
        v = v.to(tl.float32)
        
        # Update output accumulator
        o = o * alpha[:, None] + tl.dot(p.to(tl.float32), v) * beta[:, None]
        m_i = m_new
    
    # -----------------------------------------------------------
    # Write output
    o = o / l_i[:, None]
    o = o.to(tl.float16)
    
    out_offset = pid_z * stride_oz + pid_h * stride_oh
    out_ptrs = Out + out_offset + (pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] * stride_om + tl.arange(0, BLOCK_D)[None, :] * stride_od
    tl.store(out_ptrs, o, mask=(pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] < M)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        causal: Whether to apply causal masking (default True)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    # Choose kernel parameters
    BLOCK_M = 128 if M >= 2048 else 64
    BLOCK_N = 64
    BLOCK_D = min(64, Dq, Dv)
    
    # Ensure divisibility
    while Dq % BLOCK_D != 0 or Dv % BLOCK_D != 0:
        BLOCK_D //= 2
    BLOCK_D = max(BLOCK_D, 16)
    
    # Compute grid
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    # Launch kernel
    _flash_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        CAUSAL=causal,
        IS_TRAINING=False,
        num_warps=8 if BLOCK_D >= 64 else 4,
        num_stages=3
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """import torch
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
    CAUSAL: tl.constexpr,
    IS_TRAINING: tl.constexpr
):
    # -----------------------------------------------------------
    # Program ID
    pid_z = tl.program_id(0)  # batch
    pid_h = tl.program_id(1)  # head
    pid_m = tl.program_id(2)  # query block idx

    # -----------------------------------------------------------
    # Create block pointers for Q
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    q_ptrs = Q + q_offset + (pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] * stride_qm + tl.arange(0, BLOCK_D)[None, :] * stride_qd
    
    # -----------------------------------------------------------
    # Initialize pointers to K, V
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    
    # -----------------------------------------------------------
    # Initialize accumulator and stats
    o = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # -----------------------------------------------------------
    # Load Q block
    q = tl.load(q_ptrs, mask=(pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] < M, other=0.0)
    q = q.to(tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq)
    q = q * scale
    
    # -----------------------------------------------------------
    # Loop over K, V blocks
    lo = 0
    hi = N
    for block_n in range(lo, hi, BLOCK_N):
        # -------------------------------------------------------
        # Compute K block pointer and load K
        k_ptrs = K + k_offset + (block_n + tl.arange(0, BLOCK_N))[:, None] * stride_kn + tl.arange(0, BLOCK_D)[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=(block_n + tl.arange(0, BLOCK_N))[:, None] < N, other=0.0)
        k = k.to(tl.float32)
        
        # -------------------------------------------------------
        # Compute QK^T
        s = tl.dot(q, tl.trans(k))
        
        # -------------------------------------------------------
        # Apply causal masking if needed
        if CAUSAL:
            q_idx = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            k_idx = block_n + tl.arange(0, BLOCK_N)
            mask = q_idx[:, None] >= k_idx[None, :]
            s = tl.where(mask, s, float('-inf'))
        
        # -------------------------------------------------------
        # Compute statistics for this block
        m_ij = tl.max(s, axis=1)
        p = tl.exp(s - m_ij[:, None])
        
        # -------------------------------------------------------
        # Update accumulator and stats
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_i = l_i * alpha + tl.sum(p * beta[:, None], axis=1)
        
        # Load V block
        v_ptrs = V + v_offset + (block_n + tl.arange(0, BLOCK_N))[:, None] * stride_vn + tl.arange(0, BLOCK_D)[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=(block_n + tl.arange(0, BLOCK_N))[:, None] < N, other=0.0)
        v = v.to(tl.float32)
        
        # Update output accumulator
        o = o * alpha[:, None] + tl.dot(p.to(tl.float32), v) * beta[:, None]
        m_i = m_new
    
    # -----------------------------------------------------------
    # Write output
    o = o / l_i[:, None]
    o = o.to(tl.float16)
    
    out_offset = pid_z * stride_oz + pid_h * stride_oh
    out_ptrs = Out + out_offset + (pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] * stride_om + tl.arange(0, BLOCK_D)[None, :] * stride_od
    tl.store(out_ptrs, o, mask=(pid_m * BLOCK_M + tl.arange(0, BLOCK_M))[:, None] < M)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    # Choose kernel parameters
    BLOCK_M = 128 if M >= 2048 else 64
    BLOCK_N = 64
    BLOCK_D = min(64, Dq, Dv)
    
    # Ensure divisibility
    while Dq % BLOCK_D != 0 or Dv % BLOCK_D != 0:
        BLOCK_D //= 2
    BLOCK_D = max(BLOCK_D, 16)
    
    # Compute grid
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    # Launch kernel
    _flash_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        CAUSAL=causal,
        IS_TRAINING=False,
        num_warps=8 if BLOCK_D >= 64 else 4,
        num_stages=3
    )
    
    return Out
"""}
