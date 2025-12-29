import torch
import triton
import triton.language as tl
import math

@triton.jit
def sigmoid(x):
    return 1.0 / (1.0 + tl.exp(-x))

@triton.jit
def gdpa_kernel(
    # Pointers to matrices
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    # Matrix dimensions
    Z, H, M, N, Dq, Dv,
    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    IS_CAUSAL: tl.constexpr,
    HAS_GATES: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr,
):
    # Program ID
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    # Create block pointers for Q
    if USE_BLOCK_PTR:
        Q_block_ptr = tl.make_block_ptr(
            base=Q_ptr + pid_batch * stride_qz + pid_head * stride_qh,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        GQ_block_ptr = tl.make_block_ptr(
            base=GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh,
            shape=(M, Dq),
            strides=(stride_gqm, stride_gqd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        Q = tl.load(Q_block_ptr, boundary_check=(0, 1))
        if HAS_GATES:
            GQ = tl.load(GQ_block_ptr, boundary_check=(0, 1))
            Q = Q * sigmoid(GQ)
    else:
        Q_offs = (pid_batch * stride_qz + pid_head * stride_qh + 
                  offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
        Q = tl.load(Q_ptr + Q_offs, mask=offs_m[:, None] < M, other=0.0)
        if HAS_GATES:
            GQ_offs = (pid_batch * stride_gqz + pid_head * stride_gqh + 
                       offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
            GQ = tl.load(GQ_ptr + GQ_offs, mask=offs_m[:, None] < M, other=0.0)
            Q = Q * sigmoid(GQ)
    
    # Scale Q
    scale = 1.0 / tl.sqrt(tl.cast(Dq, tl.float32))
    Q_scaled = Q * scale
    
    # Initialize accumulator and stats for online softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)
    
    # Loop over N dimension
    for n_start in range(0, N, BLOCK_N):
        n_end = n_start + BLOCK_N
        
        # Load K block
        if USE_BLOCK_PTR:
            K_block_ptr = tl.make_block_ptr(
                base=K_ptr + pid_batch * stride_kz + pid_head * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            GK_block_ptr = tl.make_block_ptr(
                base=GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            K = tl.load(K_block_ptr, boundary_check=(0, 1))
            if HAS_GATES:
                GK = tl.load(GK_block_ptr, boundary_check=(0, 1))
                K = K * sigmoid(GK)
        else:
            offs_n_cur = n_start + offs_n
            K_offs = (pid_batch * stride_kz + pid_head * stride_kh + 
                      offs_n_cur[:, None] * stride_kn + offs_dq[None, :] * stride_kd)
            K = tl.load(K_ptr + K_offs, mask=offs_n_cur[:, None] < N, other=0.0)
            if HAS_GATES:
                GK_offs = (pid_batch * stride_gkz + pid_head * stride_gkh + 
                           offs_n_cur[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd)
                GK = tl.load(GK_ptr + GK_offs, mask=offs_n_cur[:, None] < N, other=0.0)
                K = K * sigmoid(GK)
        
        # Load V block
        if USE_BLOCK_PTR:
            V_block_ptr = tl.make_block_ptr(
                base=V_ptr + pid_batch * stride_vz + pid_head * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            V = tl.load(V_block_ptr, boundary_check=(0, 1))
        else:
            V_offs = (pid_batch * stride_vz + pid_head * stride_vh + 
                      offs_n_cur[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
            V = tl.load(V_ptr + V_offs, mask=offs_n_cur[:, None] < N, other=0.0)
        
        # Compute attention scores
        S = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        S = tl.dot(Q_scaled, K, out=S)
        
        # Causal masking
        if IS_CAUSAL:
            m_range = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            n_range = n_start + tl.arange(0, BLOCK_N)
            mask = m_range[:, None] >= n_range[None, :]
            S = tl.where(mask, S, float('-inf'))
        
        # Online softmax update
        m_ij = tl.max(S, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(m_ij - m_i_new)
        
        # Update l_i
        l_ij = tl.sum(tl.exp(S - m_i_new[:, None]), axis=1)
        l_i_new = alpha * l_i + beta * l_ij
        
        # Update accumulator
        scale_ratio = alpha / l_i_new[:, None]
        acc = acc * scale_ratio[:, None]
        
        # Add new contribution
        p_ij = tl.exp(S - m_i_new[:, None])
        acc += tl.dot(p_ij.to(V.dtype), V)
        
        # Update m_i and l_i for next iteration
        m_i = m_i_new
        l_i = l_i_new
    
    # Write output
    if USE_BLOCK_PTR:
        O_block_ptr = tl.make_block_ptr(
            base=O_ptr + pid_batch * stride_oz + pid_head * stride_oh,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
        tl.store(O_block_ptr, acc.to(O_ptr.dtype.element_ty), boundary_check=(0, 1))
    else:
        O_offs = (pid_batch * stride_oz + pid_head * stride_oh + 
                  offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
        tl.store(O_ptr + O_offs, acc.to(O_ptr.dtype.element_ty), 
                mask=offs_m[:, None] < M)

def gdpa_attn(
    Q: torch.Tensor, 
    K: torch.Tensor, 
    V: torch.Tensor, 
    GQ: torch.Tensor, 
    GK: torch.Tensor
) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    """
    # Check shapes
    assert Q.dim() == 4, "Q must be 4D"
    assert Q.shape == K.shape, "Q and K must have same shape except sequence length"
    assert Q.shape[:3] == GQ.shape[:3], "Q and GQ must have same first 3 dims"
    assert K.shape[:3] == GK.shape[:3], "K and GK must have same first 3 dims"
    
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    # Output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Determine kernel configuration
    def get_config(M, N, Dq, Dv):
        if Dq <= 64 and Dv <= 64:
            BLOCK_Dq = min(64, Dq)
            BLOCK_Dv = min(64, Dv)
            BLOCK_M = 128 if M >= 512 else 64
            BLOCK_N = 64 if N >= 512 else 32
        else:
            BLOCK_Dq = min(32, Dq)
            BLOCK_Dv = min(32, Dv)
            BLOCK_M = 64
            BLOCK_N = 32
        
        # Ensure divisibility
        while Dq % BLOCK_Dq != 0:
            BLOCK_Dq //= 2
        while Dv % BLOCK_Dv != 0:
            BLOCK_Dv //= 2
        
        return BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv
    
    BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv = get_config(M, N, Dq, Dv)
    
    # Grid dimensions
    grid = lambda META: (
        Z,
        H,
        triton.cdiv(M, META['BLOCK_M'])
    )
    
    # Use block pointers for larger tensors
    USE_BLOCK_PTR = M * N * Dq > 131072  # 128KB threshold
    
    # Launch kernel
    gdpa_kernel[grid](
        Q, K, V, GQ, GK, O,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv,
        IS_CAUSAL=False,
        HAS_GATES=True,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def sigmoid(x):
    return 1.0 / (1.0 + tl.exp(-x))

@triton.jit
def gdpa_kernel(
    # Pointers to matrices
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    # Matrix dimensions
    Z, H, M, N, Dq, Dv,
    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    IS_CAUSAL: tl.constexpr,
    HAS_GATES: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr,
):
    # Program ID
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    # Create block pointers for Q
    if USE_BLOCK_PTR:
        Q_block_ptr = tl.make_block_ptr(
            base=Q_ptr + pid_batch * stride_qz + pid_head * stride_qh,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        GQ_block_ptr = tl.make_block_ptr(
            base=GQ_ptr + pid_batch * stride_gqz + pid_head * stride_gqh,
            shape=(M, Dq),
            strides=(stride_gqm, stride_gqd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        Q = tl.load(Q_block_ptr, boundary_check=(0, 1))
        if HAS_GATES:
            GQ = tl.load(GQ_block_ptr, boundary_check=(0, 1))
            Q = Q * sigmoid(GQ)
    else:
        Q_offs = (pid_batch * stride_qz + pid_head * stride_qh + 
                  offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
        Q = tl.load(Q_ptr + Q_offs, mask=offs_m[:, None] < M, other=0.0)
        if HAS_GATES:
            GQ_offs = (pid_batch * stride_gqz + pid_head * stride_gqh + 
                       offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
            GQ = tl.load(GQ_ptr + GQ_offs, mask=offs_m[:, None] < M, other=0.0)
            Q = Q * sigmoid(GQ)
    
    # Scale Q
    scale = 1.0 / tl.sqrt(tl.cast(Dq, tl.float32))
    Q_scaled = Q * scale
    
    # Initialize accumulator and stats for online softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_Dv), dtype=tl.float32)
    
    # Loop over N dimension
    for n_start in range(0, N, BLOCK_N):
        n_end = n_start + BLOCK_N
        
        # Load K block
        if USE_BLOCK_PTR:
            K_block_ptr = tl.make_block_ptr(
                base=K_ptr + pid_batch * stride_kz + pid_head * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            GK_block_ptr = tl.make_block_ptr(
                base=GK_ptr + pid_batch * stride_gkz + pid_head * stride_gkh,
                shape=(N, Dq),
                strides=(stride_gkn, stride_gkd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            K = tl.load(K_block_ptr, boundary_check=(0, 1))
            if HAS_GATES:
                GK = tl.load(GK_block_ptr, boundary_check=(0, 1))
                K = K * sigmoid(GK)
        else:
            offs_n_cur = n_start + offs_n
            K_offs = (pid_batch * stride_kz + pid_head * stride_kh + 
                      offs_n_cur[:, None] * stride_kn + offs_dq[None, :] * stride_kd)
            K = tl.load(K_ptr + K_offs, mask=offs_n_cur[:, None] < N, other=0.0)
            if HAS_GATES:
                GK_offs = (pid_batch * stride_gkz + pid_head * stride_gkh + 
                           offs_n_cur[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd)
                GK = tl.load(GK_ptr + GK_offs, mask=offs_n_cur[:, None] < N, other=0.0)
                K = K * sigmoid(GK)
        
        # Load V block
        if USE_BLOCK_PTR:
            V_block_ptr = tl.make_block_ptr(
                base=V_ptr + pid_batch * stride_vz + pid_head * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            V = tl.load(V_block_ptr, boundary_check=(0, 1))
        else:
            V_offs = (pid_batch * stride_vz + pid_head * stride_vh + 
                      offs_n_cur[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
            V = tl.load(V_ptr + V_offs, mask=offs_n_cur[:, None] < N, other=0.0)
        
        # Compute attention scores
        S = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        S = tl.dot(Q_scaled, K, out=S)
        
        # Causal masking
        if IS_CAUSAL:
            m_range = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            n_range = n_start + tl.arange(0, BLOCK_N)
            mask = m_range[:, None] >= n_range[None, :]
            S = tl.where(mask, S, float('-inf'))
        
        # Online softmax update
        m_ij = tl.max(S, axis=1)
        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(m_ij - m_i_new)
        
        # Update l_i
        l_ij = tl.sum(tl.exp(S - m_i_new[:, None]), axis=1)
        l_i_new = alpha * l_i + beta * l_ij
        
        # Update accumulator
        scale_ratio = alpha / l_i_new[:, None]
        acc = acc * scale_ratio[:, None]
        
        # Add new contribution
        p_ij = tl.exp(S - m_i_new[:, None])
        acc += tl.dot(p_ij.to(V.dtype), V)
        
        # Update m_i and l_i for next iteration
        m_i = m_i_new
        l_i = l_i_new
    
    # Write output
    if USE_BLOCK_PTR:
        O_block_ptr = tl.make_block_ptr(
            base=O_ptr + pid_batch * stride_oz + pid_head * stride_oh,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
        tl.store(O_block_ptr, acc.to(O_ptr.dtype.element_ty), boundary_check=(0, 1))
    else:
        O_offs = (pid_batch * stride_oz + pid_head * stride_oh + 
                  offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
        tl.store(O_ptr + O_offs, acc.to(O_ptr.dtype.element_ty), 
                mask=offs_m[:, None] < M)

def gdpa_attn(
    Q: torch.Tensor, 
    K: torch.Tensor, 
    V: torch.Tensor, 
    GQ: torch.Tensor, 
    GK: torch.Tensor
) -> torch.Tensor:
    # Check shapes
    assert Q.dim() == 4, "Q must be 4D"
    assert Q.shape == K.shape, "Q and K must have same shape except sequence length"
    assert Q.shape[:3] == GQ.shape[:3], "Q and GQ must have same first 3 dims"
    assert K.shape[:3] == GK.shape[:3], "K and GK must have same first 3 dims"
    
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    # Output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Determine kernel configuration
    def get_config(M, N, Dq, Dv):
        if Dq <= 64 and Dv <= 64:
            BLOCK_Dq = min(64, Dq)
            BLOCK_Dv = min(64, Dv)
            BLOCK_M = 128 if M >= 512 else 64
            BLOCK_N = 64 if N >= 512 else 32
        else:
            BLOCK_Dq = min(32, Dq)
            BLOCK_Dv = min(32, Dv)
            BLOCK_M = 64
            BLOCK_N = 32
        
        # Ensure divisibility
        while Dq % BLOCK_Dq != 0:
            BLOCK_Dq //= 2
        while Dv % BLOCK_Dv != 0:
            BLOCK_Dv //= 2
        
        return BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv
    
    BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv = get_config(M, N, Dq, Dv)
    
    # Grid dimensions
    grid = lambda META: (
        Z,
        H,
        triton.cdiv(M, META['BLOCK_M'])
    )
    
    # Use block pointers for larger tensors
    USE_BLOCK_PTR = M * N * Dq > 131072  # 128KB threshold
    
    # Launch kernel
    gdpa_kernel[grid](
        Q, K, V, GQ, GK, O,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv,
        IS_CAUSAL=False,
        HAS_GATES=True,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
    )
    
    return O
"""}