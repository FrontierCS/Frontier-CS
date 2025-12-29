import torch
import triton
import triton.language as tl

@triton.jit
def gdpa_attn_kernel(
    q_ptr, k_ptr, v_ptr, gq_ptr, gk_ptr, o_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    USE_FAST_SIGMOID: tl.constexpr = True
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offset pointers for batch and head
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    gq_offset = pid_z * stride_gqz + pid_h * stride_gqh
    gk_offset = pid_z * stride_gkz + pid_h * stride_gkh
    o_offset = pid_z * stride_oz + pid_h * stride_oh
    
    # Scale factor
    scale = 1.0 / tl.sqrt(Dq)
    
    # Initialize output accumulator
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Compute query block
    m_start = pid_m * BLOCK_M
    m_end = m_start + BLOCK_M
    
    # Create block pointers for Q and GQ
    q_block_ptr = tl.make_block_ptr(
        base=q_ptr + q_offset,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    gq_block_ptr = tl.make_block_ptr(
        base=gq_ptr + gq_offset,
        shape=(M, Dq),
        strides=(stride_gqm, stride_gqd),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    # Load Q and GQ blocks
    q = tl.load(q_block_ptr, boundary_check=(0, 1))
    gq = tl.load(gq_block_ptr, boundary_check=(0, 1))
    
    # Apply gating to Q using fast sigmoid approximation
    if USE_FAST_SIGMOID:
        gq_sigmoid = 1.0 / (1.0 + tl.exp(-gq))
    else:
        gq_sigmoid = tl.sigmoid(gq)
    q_gated = q * gq_sigmoid
    
    # Process key blocks
    for n_start in range(0, N, BLOCK_N):
        n_end = n_start + BLOCK_N
        
        # Create block pointers for K, GK, and V
        k_block_ptr = tl.make_block_ptr(
            base=k_ptr + k_offset,
            shape=(N, Dq),
            strides=(stride_kn, stride_kd),
            offsets=(n_start, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        gk_block_ptr = tl.make_block_ptr(
            base=gk_ptr + gk_offset,
            shape=(N, Dq),
            strides=(stride_gkn, stride_gkd),
            offsets=(n_start, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        v_block_ptr = tl.make_block_ptr(
            base=v_ptr + v_offset,
            shape=(N, Dv),
            strides=(stride_vn, stride_vd),
            offsets=(n_start, 0),
            block_shape=(BLOCK_N, Dv),
            order=(1, 0)
        )
        
        # Load K, GK, and V blocks
        k = tl.load(k_block_ptr, boundary_check=(0, 1))
        gk = tl.load(gk_block_ptr, boundary_check=(0, 1))
        v = tl.load(v_block_ptr, boundary_check=(0, 1))
        
        # Apply gating to K using fast sigmoid approximation
        if USE_FAST_SIGMOID:
            gk_sigmoid = 1.0 / (1.0 + tl.exp(-gk))
        else:
            gk_sigmoid = tl.sigmoid(gk)
        k_gated = k * gk_sigmoid
        
        # Compute attention scores
        scores = tl.dot(q_gated, tl.trans(k_gated)) * scale
        
        # Apply mask for last block if needed
        if n_end > N:
            mask = tl.arange(0, BLOCK_N) < (N - n_start)
            scores = tl.where(mask[None, :], scores, float('-inf'))
        
        # Streaming softmax
        m_ij = tl.max(scores, axis=1)
        p = tl.exp(scores - m_ij[:, None])
        
        # Apply mask again for normalization
        if n_end > N:
            p = tl.where(mask[None, :], p, 0.0)
        
        l_ij = tl.sum(p, axis=1)
        
        # Update m_i and l_i
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        l_new = alpha * l_i + beta * l_ij
        
        # Update accumulator
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        
        # Update state
        m_i = m_new
        l_i = l_new
    
    # Normalize and store output
    acc = acc / l_i[:, None]
    
    # Create output block pointer
    o_block_ptr = tl.make_block_ptr(
        base=o_ptr + o_offset,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, Dv),
        order=(1, 0)
    )
    
    # Store output
    tl.store(o_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))

def gdpa_attn(
    Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor,
    GQ: torch.Tensor, GK: torch.Tensor
) -> torch.Tensor:
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
    N = K.shape[2]
    Dv = V.shape[3]
    
    # Allocate output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Choose block sizes based on problem size
    BLOCK_M = 128 if M >= 1024 else 64
    BLOCK_N = 128 if N >= 1024 else 64
    BLOCK_D = min(64, Dq)
    
    # Adjust block sizes if dimensions are smaller
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_D = min(BLOCK_D, Dq, Dv)
    
    # Compute grid
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    # Launch kernel
    gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        USE_FAST_SIGMOID=True,
        num_warps=8 if BLOCK_M >= 128 else 4,
        num_stages=3
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": f"""
import torch
import triton
import triton.language as tl

@triton.jit
def gdpa_attn_kernel(
    q_ptr, k_ptr, v_ptr, gq_ptr, gk_ptr, o_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    USE_FAST_SIGMOID: tl.constexpr = True
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    gq_offset = pid_z * stride_gqz + pid_h * stride_gqh
    gk_offset = pid_z * stride_gkz + pid_h * stride_gkh
    o_offset = pid_z * stride_oz + pid_h * stride_oh
    
    scale = 1.0 / tl.sqrt(Dq)
    
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    m_start = pid_m * BLOCK_M
    m_end = m_start + BLOCK_M
    
    q_block_ptr = tl.make_block_ptr(
        base=q_ptr + q_offset,
        shape=(M, Dq),
        strides=(stride_qm, stride_qd),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    gq_block_ptr = tl.make_block_ptr(
        base=gq_ptr + gq_offset,
        shape=(M, Dq),
        strides=(stride_gqm, stride_gqd),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    
    q = tl.load(q_block_ptr, boundary_check=(0, 1))
    gq = tl.load(gq_block_ptr, boundary_check=(0, 1))
    
    if USE_FAST_SIGMOID:
        gq_sigmoid = 1.0 / (1.0 + tl.exp(-gq))
    else:
        gq_sigmoid = tl.sigmoid(gq)
    q_gated = q * gq_sigmoid
    
    for n_start in range(0, N, BLOCK_N):
        n_end = n_start + BLOCK_N
        
        k_block_ptr = tl.make_block_ptr(
            base=k_ptr + k_offset,
            shape=(N, Dq),
            strides=(stride_kn, stride_kd),
            offsets=(n_start, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        gk_block_ptr = tl.make_block_ptr(
            base=gk_ptr + gk_offset,
            shape=(N, Dq),
            strides=(stride_gkn, stride_gkd),
            offsets=(n_start, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        
        v_block_ptr = tl.make_block_ptr(
            base=v_ptr + v_offset,
            shape=(N, Dv),
            strides=(stride_vn, stride_vd),
            offsets=(n_start, 0),
            block_shape=(BLOCK_N, Dv),
            order=(1, 0)
        )
        
        k = tl.load(k_block_ptr, boundary_check=(0, 1))
        gk = tl.load(gk_block_ptr, boundary_check=(0, 1))
        v = tl.load(v_block_ptr, boundary_check=(0, 1))
        
        if USE_FAST_SIGMOID:
            gk_sigmoid = 1.0 / (1.0 + tl.exp(-gk))
        else:
            gk_sigmoid = tl.sigmoid(gk)
        k_gated = k * gk_sigmoid
        
        scores = tl.dot(q_gated, tl.trans(k_gated)) * scale
        
        if n_end > N:
            mask = tl.arange(0, BLOCK_N) < (N - n_start)
            scores = tl.where(mask[None, :], scores, float('-inf'))
        
        m_ij = tl.max(scores, axis=1)
        p = tl.exp(scores - m_ij[:, None])
        
        if n_end > N:
            p = tl.where(mask[None, :], p, 0.0)
        
        l_ij = tl.sum(p, axis=1)
        
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        l_new = alpha * l_i + beta * l_ij
        
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        
        m_i = m_new
        l_i = l_new
    
    acc = acc / l_i[:, None]
    
    o_block_ptr = tl.make_block_ptr(
        base=o_ptr + o_offset,
        shape=(M, Dv),
        strides=(stride_om, stride_od),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, Dv),
        order=(1, 0)
    )
    
    tl.store(o_block_ptr, acc.to(tl.float16), boundary_check=(0, 1))

def gdpa_attn(
    Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor,
    GQ: torch.Tensor, GK: torch.Tensor
) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    BLOCK_M = 128 if M >= 1024 else 64
    BLOCK_N = 128 if N >= 1024 else 64
    BLOCK_D = min(64, Dq)
    
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_D = min(BLOCK_D, Dq, Dv)
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        USE_FAST_SIGMOID=True,
        num_warps=8 if BLOCK_M >= 128 else 4,
        num_stages=3
    )
    
    return O
"""}