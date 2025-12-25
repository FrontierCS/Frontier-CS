import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q,  # [M, D]
    K,  # [N, D]
    V,  # [N, Dv]
    row_lens,  # [M]
    Out,  # [M, Dv]
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_out_m, stride_out_d,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Load row lengths for this block of queries
    row_len_ptrs = row_lens + offs_m
    row_lens_i = tl.load(row_len_ptrs, mask=offs_m < M, other=0)
    max_row_len = tl.max(row_lens_i, axis=0)
    
    # Initialize accumulators for output and softmax
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Pointers to Q block
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    
    # Process keys in blocks
    for start_n in range(0, max_row_len, BLOCK_N):
        key_n = start_n + offs_n
        
        # Compute mask: key_n < row_lens_i for each query
        mask_n = key_n[None, :] < row_lens_i[:, None]
        
        # Load K block
        k_ptrs = K + (key_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Load V block
        v_ptrs = V + (key_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute Q @ K^T for this block
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        scores = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        
        # Tiled matmul for better memory efficiency
        for start_d in range(0, D, BLOCK_D):
            offs_d_tile = start_d + offs_d
            mask_d = offs_d_tile < D
            
            q_tile = tl.load(q_ptrs, mask=mask_d[None, :] & (offs_m[:, None] < M), other=0.0)
            k_tile = tl.load(k_ptrs, mask=mask_d[None, :] & mask_n[:, None], other=0.0)
            
            scores += tl.dot(q_tile, tl.trans(k_tile))
        
        scores = scores * scale
        scores = tl.where(mask_n, scores, float('-inf'))
        
        # Streaming softmax update
        m_new = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(scores - m_new[:, None])
        l_new = alpha * l_i + tl.sum(beta, axis=1)
        
        # Update accumulators
        scale_old = alpha * (l_i / l_new)
        scale_new = 1.0 / l_new
        
        acc = acc * scale_old[:, None]
        
        # Weighted sum of values
        p = beta * scale_new[:, None]
        acc += tl.dot(p, v)
        
        # Update softmax states
        m_i = m_new
        l_i = l_new
    
    # Store output
    out_ptrs = Out + (offs_m[:, None] * stride_out_m + offs_dv[None, :] * stride_out_d)
    tl.store(out_ptrs, acc, mask=offs_m[:, None] < M)


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert row_lens.dtype in (torch.int32, torch.int64)
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    Out = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    scale = 1.0 / (D ** 0.5)
    
    # Choose block sizes based on hardware
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 32
    BLOCK_DV = 32
    
    grid = (triton.cdiv(M, BLOCK_M),)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, Out,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        Out.stride(0), Out.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q,  # [M, D]
    K,  # [N, D]
    V,  # [N, Dv]
    row_lens,  # [M]
    Out,  # [M, Dv]
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_out_m, stride_out_d,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Load row lengths for this block of queries
    row_len_ptrs = row_lens + offs_m
    row_lens_i = tl.load(row_len_ptrs, mask=offs_m < M, other=0)
    max_row_len = tl.max(row_lens_i, axis=0)
    
    # Initialize accumulators for output and softmax
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Pointers to Q block
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    
    # Process keys in blocks
    for start_n in range(0, max_row_len, BLOCK_N):
        key_n = start_n + offs_n
        
        # Compute mask: key_n < row_lens_i for each query
        mask_n = key_n[None, :] < row_lens_i[:, None]
        
        # Load K block
        k_ptrs = K + (key_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Load V block
        v_ptrs = V + (key_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute Q @ K^T for this block
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        scores = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        
        # Tiled matmul for better memory efficiency
        for start_d in range(0, D, BLOCK_D):
            offs_d_tile = start_d + offs_d
            mask_d = offs_d_tile < D
            
            q_tile = tl.load(q_ptrs, mask=mask_d[None, :] & (offs_m[:, None] < M), other=0.0)
            k_tile = tl.load(k_ptrs, mask=mask_d[None, :] & mask_n[:, None], other=0.0)
            
            scores += tl.dot(q_tile, tl.trans(k_tile))
        
        scores = scores * scale
        scores = tl.where(mask_n, scores, float('-inf'))
        
        # Streaming softmax update
        m_new = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(scores - m_new[:, None])
        l_new = alpha * l_i + tl.sum(beta, axis=1)
        
        # Update accumulators
        scale_old = alpha * (l_i / l_new)
        scale_new = 1.0 / l_new
        
        acc = acc * scale_old[:, None]
        
        # Weighted sum of values
        p = beta * scale_new[:, None]
        acc += tl.dot(p, v)
        
        # Update softmax states
        m_i = m_new
        l_i = l_new
    
    # Store output
    out_ptrs = Out + (offs_m[:, None] * stride_out_m + offs_dv[None, :] * stride_out_d)
    tl.store(out_ptrs, acc, mask=offs_m[:, None] < M)


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert row_lens.dtype in (torch.int32, torch.int64)
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    Out = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    scale = 1.0 / (D ** 0.5)
    
    # Choose block sizes based on hardware
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 32
    BLOCK_DV = 32
    
    grid = (triton.cdiv(M, BLOCK_M),)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, Out,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        Out.stride(0), Out.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
    )
    
    return Out
"""}
