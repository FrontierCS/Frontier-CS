import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, O, row_lens,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    NUM_STAGES: tl.constexpr,
    NUM_WARPS: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    q_ptr = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptr = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    v_ptr = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
    o_ptr = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    
    # Load row lengths for the current block of queries
    row_lens_m = tl.load(row_lens + offs_m, mask=offs_m < M, other=0)
    
    # Initialize accumulator and max for streaming softmax
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Compute number of N blocks for these queries
    max_n = tl.max(row_lens_m)
    num_n_blocks = tl.cdiv(max_n, BLOCK_N)
    
    # Loop over N blocks with double buffering
    for n_block in range(num_n_blocks):
        n_start = n_block * BLOCK_N
        n_offs = n_start + tl.arange(0, BLOCK_N)
        
        # Create mask for valid keys (j < row_lens[i])
        valid_mask = n_offs[None, :] < row_lens_m[:, None]
        
        # Load Q block (BLOCK_M x BLOCK_D)
        q = tl.load(q_ptr, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
        
        # Load K block (BLOCK_N x BLOCK_D)
        k = tl.load(k_ptr + n_start * stride_kn, 
                   mask=(n_offs[:, None] < N) & (offs_d[None, :] < D), 
                   other=0.0).to(tl.float32)
        
        # Compute QK^T (BLOCK_M x BLOCK_N)
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        # Apply row-wise masking
        s = tl.where(valid_mask, s, float('-inf'))
        
        # Streaming softmax update
        m_new = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        alpha = tl.exp(m_i[:, None] - m_new[:, None])
        p = tl.exp(s - m_new[:, None])
        l_new = alpha * l_i[:, None] + tl.sum(p, axis=1)
        
        # Load V block (BLOCK_N x BLOCK_DV)
        v = tl.load(v_ptr + n_start * stride_vn,
                   mask=(n_offs[:, None] < N) & (offs_dv[None, :] < Dv),
                   other=0.0).to(tl.float32)
        
        # Update accumulator
        acc = acc * alpha + tl.dot(p, v)
        
        # Update state
        m_i = m_new
        l_i = l_new
    
    # Final normalization
    acc = acc / l_i[:, None]
    
    # Store output
    tl.store(o_ptr, acc.to(tl.float16), 
            mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

@triton.jit
def _ragged_attn_fwd_small_kernel(
    Q, K, V, O, row_lens,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    q_ptr = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    o_ptr = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    
    # Load row lengths for these queries
    row_lens_m = tl.load(row_lens + offs_m, mask=offs_m < M, other=0)
    
    # Load Q block
    q = tl.load(q_ptr, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    # Initialize accumulator and softmax state
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process keys in blocks
    max_n = tl.max(row_lens_m)
    num_n_blocks = tl.cdiv(max_n, BLOCK_N)
    
    for n_block in range(num_n_blocks):
        n_start = n_block * BLOCK_N
        n_offs = n_start + tl.arange(0, BLOCK_N)
        
        # Create mask for valid keys
        valid_mask = n_offs[None, :] < row_lens_m[:, None]
        
        # Load K block
        k_ptr_block = K + n_offs[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptr_block,
                   mask=(n_offs[:, None] < N) & (offs_d[None, :] < D),
                   other=0.0).to(tl.float32)
        
        # Compute scores
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        s = tl.where(valid_mask, s, float('-inf'))
        
        # Update softmax
        m_new = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        alpha = tl.exp(m_i[:, None] - m_new[:, None])
        p = tl.exp(s - m_new[:, None])
        l_new = alpha * l_i[:, None] + tl.sum(p, axis=1)
        
        # Load V block
        v_ptr_block = V + n_offs[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptr_block,
                   mask=(n_offs[:, None] < N) & (offs_dv[None, :] < Dv),
                   other=0.0).to(tl.float32)
        
        # Update accumulator
        acc = acc * alpha + tl.dot(p, v)
        
        m_i = m_new
        l_i = l_new
    
    # Normalize and store
    acc = acc / l_i[:, None]
    tl.store(o_ptr, acc.to(tl.float16),
            mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    assert D == D_k, f"Q dimension {D} must match K dimension {D_k}"
    assert N == N_v, f"K rows {N} must match V rows {N_v}"
    
    # Create output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    # Scale factor
    scale = 1.0 / math.sqrt(D)
    
    # Choose kernel configuration based on problem size
    if M <= 512 and D <= 64 and Dv <= 64:
        # Use small kernel for better occupancy
        BLOCK_M = 64
        BLOCK_N = 64
        BLOCK_D = min(64, triton.next_power_of_2(D))
        BLOCK_DV = min(64, triton.next_power_of_2(Dv))
        
        grid = (triton.cdiv(M, BLOCK_M),)
        
        kernel = _ragged_attn_fwd_small_kernel
    else:
        # Use larger, more optimized kernel
        BLOCK_M = 32
        BLOCK_N = 64
        BLOCK_D = 32
        BLOCK_DV = 32
        NUM_STAGES = 3
        NUM_WARPS = 4
        
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        
        kernel = _ragged_attn_fwd_kernel
    
    # Launch kernel
    kernel[grid](
        Q, K, V, O, row_lens,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        NUM_STAGES=NUM_STAGES if 'NUM_STAGES' in kernel.arg_names else 1,
        NUM_WARPS=NUM_WARPS if 'NUM_WARPS' in kernel.arg_names else 4
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
def _ragged_attn_fwd_kernel(
    Q, K, V, O, row_lens,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    NUM_STAGES: tl.constexpr,
    NUM_WARPS: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    q_ptr = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptr = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    v_ptr = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
    o_ptr = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    
    # Load row lengths for the current block of queries
    row_lens_m = tl.load(row_lens + offs_m, mask=offs_m < M, other=0)
    
    # Initialize accumulator and max for streaming softmax
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Compute number of N blocks for these queries
    max_n = tl.max(row_lens_m)
    num_n_blocks = tl.cdiv(max_n, BLOCK_N)
    
    # Loop over N blocks with double buffering
    for n_block in range(num_n_blocks):
        n_start = n_block * BLOCK_N
        n_offs = n_start + tl.arange(0, BLOCK_N)
        
        # Create mask for valid keys (j < row_lens[i])
        valid_mask = n_offs[None, :] < row_lens_m[:, None]
        
        # Load Q block (BLOCK_M x BLOCK_D)
        q = tl.load(q_ptr, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
        
        # Load K block (BLOCK_N x BLOCK_D)
        k = tl.load(k_ptr + n_start * stride_kn, 
                   mask=(n_offs[:, None] < N) & (offs_d[None, :] < D), 
                   other=0.0).to(tl.float32)
        
        # Compute QK^T (BLOCK_M x BLOCK_N)
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        # Apply row-wise masking
        s = tl.where(valid_mask, s, float('-inf'))
        
        # Streaming softmax update
        m_new = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        alpha = tl.exp(m_i[:, None] - m_new[:, None])
        p = tl.exp(s - m_new[:, None])
        l_new = alpha * l_i[:, None] + tl.sum(p, axis=1)
        
        # Load V block (BLOCK_N x BLOCK_DV)
        v = tl.load(v_ptr + n_start * stride_vn,
                   mask=(n_offs[:, None] < N) & (offs_dv[None, :] < Dv),
                   other=0.0).to(tl.float32)
        
        # Update accumulator
        acc = acc * alpha + tl.dot(p, v)
        
        # Update state
        m_i = m_new
        l_i = l_new
    
    # Final normalization
    acc = acc / l_i[:, None]
    
    # Store output
    tl.store(o_ptr, acc.to(tl.float16), 
            mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

@triton.jit
def _ragged_attn_fwd_small_kernel(
    Q, K, V, O, row_lens,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    q_ptr = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    o_ptr = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    
    # Load row lengths for these queries
    row_lens_m = tl.load(row_lens + offs_m, mask=offs_m < M, other=0)
    
    # Load Q block
    q = tl.load(q_ptr, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    # Initialize accumulator and softmax state
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process keys in blocks
    max_n = tl.max(row_lens_m)
    num_n_blocks = tl.cdiv(max_n, BLOCK_N)
    
    for n_block in range(num_n_blocks):
        n_start = n_block * BLOCK_N
        n_offs = n_start + tl.arange(0, BLOCK_N)
        
        # Create mask for valid keys
        valid_mask = n_offs[None, :] < row_lens_m[:, None]
        
        # Load K block
        k_ptr_block = K + n_offs[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptr_block,
                   mask=(n_offs[:, None] < N) & (offs_d[None, :] < D),
                   other=0.0).to(tl.float32)
        
        # Compute scores
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        s = tl.where(valid_mask, s, float('-inf'))
        
        # Update softmax
        m_new = tl.maximum(m_i[:, None], tl.max(s, axis=1))
        alpha = tl.exp(m_i[:, None] - m_new[:, None])
        p = tl.exp(s - m_new[:, None])
        l_new = alpha * l_i[:, None] + tl.sum(p, axis=1)
        
        # Load V block
        v_ptr_block = V + n_offs[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptr_block,
                   mask=(n_offs[:, None] < N) & (offs_dv[None, :] < Dv),
                   other=0.0).to(tl.float32)
        
        # Update accumulator
        acc = acc * alpha + tl.dot(p, v)
        
        m_i = m_new
        l_i = l_new
    
    # Normalize and store
    acc = acc / l_i[:, None]
    tl.store(o_ptr, acc.to(tl.float16),
            mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    assert D == D_k, f"Q dimension {D} must match K dimension {D_k}"
    assert N == N_v, f"K rows {N} must match V rows {N_v}"
    
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    scale = 1.0 / math.sqrt(D)
    
    if M <= 512 and D <= 64 and Dv <= 64:
        BLOCK_M = 64
        BLOCK_N = 64
        BLOCK_D = min(64, triton.next_power_of_2(D))
        BLOCK_DV = min(64, triton.next_power_of_2(Dv))
        
        grid = (triton.cdiv(M, BLOCK_M),)
        
        kernel = _ragged_attn_fwd_small_kernel
    else:
        BLOCK_M = 32
        BLOCK_N = 64
        BLOCK_D = 32
        BLOCK_DV = 32
        NUM_STAGES = 3
        NUM_WARPS = 4
        
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        
        kernel = _ragged_attn_fwd_kernel
    
    kernel[grid](
        Q, K, V, O, row_lens,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        NUM_STAGES=NUM_STAGES if 'NUM_STAGES' in kernel.arg_names else 1,
        NUM_WARPS=NUM_WARPS if 'NUM_WARPS' in kernel.arg_names else 4
    )
    
    return O
"""}