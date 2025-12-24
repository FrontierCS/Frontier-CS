import torch
import triton
import triton.language as tl
import numpy as np

@triton.jit
def _ragged_attention_fwd_kernel(
    Q, K, V, O,
    row_lens,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    USE_MASK: tl.constexpr,
    SCALE: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Load row length for this query row
    row_len = tl.load(row_lens + pid_m)
    
    # Initialize pointers
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Mask for valid queries
    mask_m = offs_m < M
    
    # Initialize accumulators for online softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Accumulator for output
    acc_o = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    
    # Load query block
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    # Loop over key blocks
    for start_n in range(0, N, BLOCK_N):
        # Compute key block index
        n_idx = start_n + offs_n
        
        # Mask for valid keys within row_len
        mask_n = n_idx < row_len
        mask_kv = mask_m[:, None] & mask_n[None, :] & (offs_d[None, :] < D)
        
        # Load key block
        k_ptrs = K + (n_idx[None, :] * stride_kn + offs_d[:, None] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_kv, other=0.0).to(tl.float32)
        
        # Compute scores: Q @ K^T
        scores = tl.dot(q, k, out_dtype=tl.float32) * SCALE
        
        # Apply mask for keys beyond row_len
        if USE_MASK:
            mask_n_full = n_idx[None, :] < row_len
            scores = tl.where(mask_n_full, scores, float('-inf'))
        
        # Online softmax update
        m_i_new = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(scores - m_i_new[:, None])
        
        # Update softmax denominator
        l_i = l_i * alpha + tl.sum(beta, axis=1)
        
        # Update output accumulator
        # Load value block
        v_ptrs = V + (n_idx[None, :] * stride_vn + offs_dv[:, None] * stride_vd)
        v = tl.load(v_ptrs, 
                   mask=mask_m[:, None] & mask_n[None, :] & (offs_dv[:, None] < Dv), 
                   other=0.0).to(tl.float32)
        
        # Update output with scaled values
        beta_scaled = beta / l_i[:, None]
        acc_o += tl.dot(beta_scaled.to(v.dtype), tl.trans(v))
        
        # Update m_i for next iteration
        m_i = m_i_new
    
    # Store output
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dv = tl.arange(0, BLOCK_DV)
    mask_store = mask_m[:, None] & (offs_dv[None, :] < Dv)
    o_ptrs = O + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, acc_o.to(O.dtype.element_ty), mask=mask_store)

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
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension D"
    assert K.size(0) == V.size(0), "K and V must have same sequence length N"
    
    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]
    
    # Output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Scale factor
    scale = 1.0 / (D ** 0.5)
    
    # Choose block sizes based on hardware constraints
    BLOCK_M = 64 if M >= 64 else 32
    BLOCK_N = 64
    BLOCK_D = min(D, 64)
    BLOCK_DV = min(Dv, 64)
    
    # Ensure block sizes are powers of two for better performance
    BLOCK_M = 1 << int(np.log2(BLOCK_M))
    BLOCK_N = 1 << int(np.log2(BLOCK_N))
    BLOCK_D = 1 << int(np.log2(BLOCK_D))
    BLOCK_DV = 1 << int(np.log2(BLOCK_DV))
    
    # Grid configuration
    grid = (triton.cdiv(M, BLOCK_M), 1)
    
    # Launch kernel
    _ragged_attention_fwd_kernel[grid](
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
        USE_MASK=True,
        SCALE=scale
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = '''
import torch
import triton
import triton.language as tl
import numpy as np

@triton.jit
def _ragged_attention_fwd_kernel(
    Q, K, V, O,
    row_lens,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    USE_MASK: tl.constexpr,
    SCALE: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Load row length for this query row
    row_len = tl.load(row_lens + pid_m)
    
    # Initialize pointers
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Mask for valid queries
    mask_m = offs_m < M
    
    # Initialize accumulators for online softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Accumulator for output
    acc_o = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    
    # Load query block
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)
    
    # Loop over key blocks
    for start_n in range(0, N, BLOCK_N):
        # Compute key block index
        n_idx = start_n + offs_n
        
        # Mask for valid keys within row_len
        mask_n = n_idx < row_len
        mask_kv = mask_m[:, None] & mask_n[None, :] & (offs_d[None, :] < D)
        
        # Load key block
        k_ptrs = K + (n_idx[None, :] * stride_kn + offs_d[:, None] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_kv, other=0.0).to(tl.float32)
        
        # Compute scores: Q @ K^T
        scores = tl.dot(q, k, out_dtype=tl.float32) * SCALE
        
        # Apply mask for keys beyond row_len
        if USE_MASK:
            mask_n_full = n_idx[None, :] < row_len
            scores = tl.where(mask_n_full, scores, float('-inf'))
        
        # Online softmax update
        m_i_new = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(scores - m_i_new[:, None])
        
        # Update softmax denominator
        l_i = l_i * alpha + tl.sum(beta, axis=1)
        
        # Update output accumulator
        # Load value block
        v_ptrs = V + (n_idx[None, :] * stride_vn + offs_dv[:, None] * stride_vd)
        v = tl.load(v_ptrs, 
                   mask=mask_m[:, None] & mask_n[None, :] & (offs_dv[:, None] < Dv), 
                   other=0.0).to(tl.float32)
        
        # Update output with scaled values
        beta_scaled = beta / l_i[:, None]
        acc_o += tl.dot(beta_scaled.to(v.dtype), tl.trans(v))
        
        # Update m_i for next iteration
        m_i = m_i_new
    
    # Store output
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dv = tl.arange(0, BLOCK_DV)
    mask_store = mask_m[:, None] & (offs_dv[None, :] < Dv)
    o_ptrs = O + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, acc_o.to(O.dtype.element_ty), mask=mask_store)

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
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension D"
    assert K.size(0) == V.size(0), "K and V must have same sequence length N"
    
    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]
    
    # Output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Scale factor
    scale = 1.0 / (D ** 0.5)
    
    # Choose block sizes based on hardware constraints
    BLOCK_M = 64 if M >= 64 else 32
    BLOCK_N = 64
    BLOCK_D = min(D, 64)
    BLOCK_DV = min(Dv, 64)
    
    # Ensure block sizes are powers of two for better performance
    BLOCK_M = 1 << int(np.log2(BLOCK_M))
    BLOCK_N = 1 << int(np.log2(BLOCK_N))
    BLOCK_D = 1 << int(np.log2(BLOCK_D))
    BLOCK_DV = 1 << int(np.log2(BLOCK_DV))
    
    # Grid configuration
    grid = (triton.cdiv(M, BLOCK_M), 1)
    
    # Launch kernel
    _ragged_attention_fwd_kernel[grid](
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
        USE_MASK=True,
        SCALE=scale
    )
    
    return O
'''
        return {"code": code}
