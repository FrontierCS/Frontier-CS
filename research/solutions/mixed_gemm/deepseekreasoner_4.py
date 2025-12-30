import torch
import triton
import triton.language as tl
import math

@triton.jit
def linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    USE_FP16_ACC: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_K) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptr, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptr, mask=mask_w, other=0.0).to(tl.float32)
        
        if USE_FP16_ACC:
            accumulator += tl.dot(x, w, out_dtype=tl.float16).to(tl.float32)
        else:
            accumulator += tl.dot(x, w, out_dtype=tl.float32)
        
        X_ptr += BLOCK_K * stride_xk
        W_ptr += BLOCK_K * stride_wk
    
    if N == 1:
        bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)
    else:
        bias_ptrs = B_ptr + offs_n[None, :] * stride_bn
        bias = tl.load(bias_ptrs, mask=offs_n[None, :] < N, other=0.0)
    
    accumulator += bias
    
    # GELU approximation: 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))
    # More efficient than using erf
    x = accumulator
    gelu = x * 0.5 * (1.0 + tl.tanh(0.7978845608 * (x + 0.044715 * x * x * x)))
    
    Y_ptr += offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    mask_y = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptr, gelu.to(tl.float16), mask=mask_y)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X has K={K}, W has K={K_check}"
    assert B.shape[0] == N, f"Bias shape mismatch: B has {B.shape[0]}, expected {N}"
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    
    # Choose optimal configuration based on matrix size
    if M >= 1024 and N >= 1024 and K >= 1024:
        # Large matrices - use larger blocks
        config = {
            'BLOCK_M': 64,
            'BLOCK_N': 128,
            'BLOCK_K': 64,
            'USE_FP16_ACC': False,
        }
    elif M <= 512 or N <= 512:
        # Smaller matrices - use smaller blocks
        config = {
            'BLOCK_M': 32,
            'BLOCK_N': 64,
            'BLOCK_K': 32,
            'USE_FP16_ACC': True,
        }
    else:
        # Medium matrices
        config = {
            'BLOCK_M': 64,
            'BLOCK_N': 64,
            'BLOCK_K': 32,
            'USE_FP16_ACC': False,
        }
    
    linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
        **config
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
import math

@triton.jit
def linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    USE_FP16_ACC: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_K) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptr, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptr, mask=mask_w, other=0.0).to(tl.float32)
        
        if USE_FP16_ACC:
            accumulator += tl.dot(x, w, out_dtype=tl.float16).to(tl.float32)
        else:
            accumulator += tl.dot(x, w, out_dtype=tl.float32)
        
        X_ptr += BLOCK_K * stride_xk
        W_ptr += BLOCK_K * stride_wk
    
    if N == 1:
        bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)
    else:
        bias_ptrs = B_ptr + offs_n[None, :] * stride_bn
        bias = tl.load(bias_ptrs, mask=offs_n[None, :] < N, other=0.0)
    
    accumulator += bias
    
    # GELU approximation: 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))
    x = accumulator
    gelu = x * 0.5 * (1.0 + tl.tanh(0.7978845608 * (x + 0.044715 * x * x * x)))
    
    Y_ptr += offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    mask_y = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptr, gelu.to(tl.float16), mask=mask_y)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X has K={K}, W has K={K_check}"
    assert B.shape[0] == N, f"Bias shape mismatch: B has {B.shape[0]}, expected {N}"
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    
    # Choose optimal configuration based on matrix size
    if M >= 1024 and N >= 1024 and K >= 1024:
        # Large matrices - use larger blocks
        config = {
            'BLOCK_M': 64,
            'BLOCK_N': 128,
            'BLOCK_K': 64,
            'USE_FP16_ACC': False,
        }
    elif M <= 512 or N <= 512:
        # Smaller matrices - use smaller blocks
        config = {
            'BLOCK_M': 32,
            'BLOCK_N': 64,
            'BLOCK_K': 32,
            'USE_FP16_ACC': True,
        }
    else:
        # Medium matrices
        config = {
            'BLOCK_M': 64,
            'BLOCK_N': 64,
            'BLOCK_K': 32,
            'USE_FP16_ACC': False,
        }
    
    linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
        **config
    )
    
    return Y
'''
        return {"code": code}