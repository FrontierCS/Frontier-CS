import torch
import triton
import triton.language as tl
from typing import Dict

@triton.jit
def linear_gelu_kernel(
    # Pointers to matrices
    X_ptr, W_ptr, B_ptr, Out_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m, stride_out_n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    USE_FP16_ACCUM: tl.constexpr = False,
):
    # Program ID
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Create block pointers
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Compute pointers for X block
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    # Compute pointers for W block  
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    # Initialize accumulator
    if USE_FP16_ACCUM:
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float16)
    else:
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Loop over K dimension
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Load X block
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        x = tl.load(X_ptrs, mask=x_mask, other=0.0)
        
        # Load W block
        w_mask = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        w = tl.load(W_ptrs, mask=w_mask, other=0.0)
        
        # Matrix multiplication
        if USE_FP16_ACCUM:
            acc += tl.dot(x, w, out_dtype=tl.float16)
        else:
            acc += tl.dot(x, w, out_dtype=tl.float32)
        
        # Update pointers for next block
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk
    
    # Add bias
    b_ptrs = B_ptr + offs_n * stride_bn
    b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
    acc += b[None, :]
    
    # Apply GELU activation using libdevice.erf
    # GELU formula: x * 0.5 * (1.0 + erf(x * 0.7071067811865476))
    if not USE_FP16_ACCUM:
        acc = acc.to(tl.float32)
    
    # Constants for GELU
    sqrt_2_over_pi = 0.7071067811865476
    one_half = 0.5
    one = 1.0
    
    # Compute GELU
    x_scaled = acc * sqrt_2_over_pi
    erf_result = tl.extra.cuda.libdevice.erf(x_scaled)
    gelu = acc * one_half * (one + erf_result)
    
    # Convert back to fp16 for output
    output = gelu.to(tl.float16)
    
    # Write output
    out_ptrs = Out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(out_ptrs, output, mask=out_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
    
    Returns:
        Output tensor of shape (M, N) - output with GELU activation (float16)
    """
    # Check shapes
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X K={K}, W K={K_check}"
    assert B.shape[0] == N, f"Bias shape mismatch: B N={B.shape[0]}, W N={N}"
    
    # Allocate output
    out = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # Choose kernel configuration based on matrix size
    if M >= 1024 and N >= 4096:
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 128
        BLOCK_SIZE_K = 32
        num_warps = 8
    else:
        BLOCK_SIZE_M = 64
        BLOCK_SIZE_N = 64
        BLOCK_SIZE_K = 32
        num_warps = 4
    
    # Ensure blocks don't exceed dimensions
    BLOCK_SIZE_M = min(BLOCK_SIZE_M, M)
    BLOCK_SIZE_N = min(BLOCK_SIZE_N, N)
    
    # Grid dimensions
    grid = (
        triton.cdiv(M, BLOCK_SIZE_M),
        triton.cdiv(N, BLOCK_SIZE_N),
    )
    
    # Launch kernel
    linear_gelu_kernel[grid](
        X, W, B, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        out.stride(0), out.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        USE_FP16_ACCUM=False,  # Use fp32 accumulation for numerical stability
        num_warps=num_warps,
        num_stages=3,
    )
    
    return out

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def linear_gelu_kernel(
    # Pointers to matrices
    X_ptr, W_ptr, B_ptr, Out_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_out_m, stride_out_n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    USE_FP16_ACCUM: tl.constexpr = False,
):
    # Program ID
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Create block pointers
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Compute pointers for X block
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    # Compute pointers for W block  
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    # Initialize accumulator
    if USE_FP16_ACCUM:
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float16)
    else:
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Loop over K dimension
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Load X block
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        x = tl.load(X_ptrs, mask=x_mask, other=0.0)
        
        # Load W block
        w_mask = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        w = tl.load(W_ptrs, mask=w_mask, other=0.0)
        
        # Matrix multiplication
        if USE_FP16_ACCUM:
            acc += tl.dot(x, w, out_dtype=tl.float16)
        else:
            acc += tl.dot(x, w, out_dtype=tl.float32)
        
        # Update pointers for next block
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk
    
    # Add bias
    b_ptrs = B_ptr + offs_n * stride_bn
    b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
    acc += b[None, :]
    
    # Apply GELU activation using libdevice.erf
    # GELU formula: x * 0.5 * (1.0 + erf(x * 0.7071067811865476))
    if not USE_FP16_ACCUM:
        acc = acc.to(tl.float32)
    
    # Constants for GELU
    sqrt_2_over_pi = 0.7071067811865476
    one_half = 0.5
    one = 1.0
    
    # Compute GELU
    x_scaled = acc * sqrt_2_over_pi
    erf_result = tl.extra.cuda.libdevice.erf(x_scaled)
    gelu = acc * one_half * (one + erf_result)
    
    # Convert back to fp16 for output
    output = gelu.to(tl.float16)
    
    # Write output
    out_ptrs = Out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(out_ptrs, output, mask=out_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
    
    Returns:
        Output tensor of shape (M, N) - output with GELU activation (float16)
    """
    # Check shapes
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X K={K}, W K={K_check}"
    assert B.shape[0] == N, f"Bias shape mismatch: B N={B.shape[0]}, W N={N}"
    
    # Allocate output
    out = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # Choose kernel configuration based on matrix size
    if M >= 1024 and N >= 4096:
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 128
        BLOCK_SIZE_K = 32
        num_warps = 8
    else:
        BLOCK_SIZE_M = 64
        BLOCK_SIZE_N = 64
        BLOCK_SIZE_K = 32
        num_warps = 4
    
    # Ensure blocks don't exceed dimensions
    BLOCK_SIZE_M = min(BLOCK_SIZE_M, M)
    BLOCK_SIZE_N = min(BLOCK_SIZE_N, N)
    
    # Grid dimensions
    grid = (
        triton.cdiv(M, BLOCK_SIZE_M),
        triton.cdiv(N, BLOCK_SIZE_N),
    )
    
    # Launch kernel
    linear_gelu_kernel[grid](
        X, W, B, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        out.stride(0), out.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        USE_FP16_ACCUM=False,  # Use fp32 accumulation for numerical stability
        num_warps=num_warps,
        num_stages=3,
    )
    
    return out
'''
        return {"code": code}
