import torch
import triton
import triton.language as tl
from typing import Optional

@triton.jit
def _ragged_attention_kernel(
    Q,  # [M, D] - query matrix
    K,  # [N, D] - key matrix  
    V,  # [N, Dv] - value matrix
    row_lens,  # [M] - row lengths
    O,  # [M, Dv] - output matrix
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    USE_FP32_ACC: tl.constexpr = True,
):
    # Program ID
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Offsets for this program
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Load row lengths for this block of queries
    row_lens_m = tl.load(row_lens + offs_m, mask=offs_m < M, other=0)
    
    # Initialize accumulator for softmax
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32 if USE_FP32_ACC else tl.float16)
    
    # Load query block [BLOCK_M, D]
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0)
    q = q.to(tl.float32)
    
    # Loop over key blocks
    for start_n in range(0, N, BLOCK_N):
        n_idx = start_n + offs_n[None, :]
        
        # Load key block [BLOCK_N, D]
        k_ptrs = K + (n_idx * stride_kn + offs_d[:, None] * stride_kd)
        k = tl.load(k_ptrs, mask=(n_idx < N) & (offs_d[:, None] < D), other=0.0)
        k = k.to(tl.float32)
        
        # Compute QK^T [BLOCK_M, BLOCK_N]
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        qk += tl.dot(q, k, allow_tf32=False)
        qk *= scale
        
        # Create mask for ragged attention
        mask = n_idx < row_lens_m[:, None]
        qk = tl.where(mask, qk, float('-inf'))
        
        # Streaming softmax update
        m_i_new = tl.maximum(m_i, tl.max(qk, axis=1))
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(qk - m_i_new[:, None])
        
        # Update running statistics
        l_i = l_i * alpha + tl.sum(beta, axis=1)
        
        # Load value block [BLOCK_N, Dv]
        v_ptrs = V + (n_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=(n_idx[:, None] < N) & (offs_dv[None, :] < Dv), other=0.0)
        v = v.to(tl.float32 if USE_FP32_ACC else tl.float16)
        
        # Update accumulator with correction
        acc = acc * alpha[:, None] + tl.dot(beta, v, allow_tf32=False)
        m_i = m_i_new
    
    # Normalize and store output
    acc = acc / l_i[:, None]
    acc = acc.to(tl.float16)
    
    # Store output [BLOCK_M, Dv]
    o_ptrs = O + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

def ragged_attn(
    Q: torch.Tensor,
    K: torch.Tensor, 
    V: torch.Tensor,
    row_lens: torch.Tensor
) -> torch.Tensor:
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
    # Check inputs
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension"
    assert K.size(0) == V.size(0), "K and V must have same sequence length"
    assert row_lens.size(0) == Q.size(0), "row_lens must match Q batch size"
    
    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]
    
    # Output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Heuristic for block sizes based on hardware
    # L4 GPU: 24GB VRAM, 60 SMs
    if D <= 64:
        BLOCK_D = 64
    elif D <= 128:
        BLOCK_D = 64
    else:
        BLOCK_D = 32
        
    if Dv <= 64:
        BLOCK_DV = 64
    elif Dv <= 128:
        BLOCK_DV = 64
    else:
        BLOCK_DV = 32
    
    # Set block sizes - tuned for L4 GPU
    BLOCK_M = 64  # Queries per block
    BLOCK_N = 64  # Keys per block
    
    # Ensure block sizes don't exceed dimensions
    BLOCK_D = min(BLOCK_D, D)
    BLOCK_DV = min(BLOCK_DV, Dv)
    
    # Scale factor
    scale = 1.0 / (D ** 0.5)
    
    # Grid
    grid = (triton.cdiv(M, BLOCK_M), 1)
    
    # Launch kernel
    _ragged_attention_kernel[grid](
        Q, K, V, row_lens, O,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale=scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        USE_FP32_ACC=True,
        num_warps=4,
        num_stages=3,
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Return the code as a string
        import inspect
        code = inspect.getsource(_ragged_attention_kernel) + "\n\n" + inspect.getsource(ragged_attn)
        return {"code": code}