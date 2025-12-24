import torch
import triton
import triton.language as tl
import math

@triton.jit
def _gelu_activation(x):
    """Fast approximation of GELU activation."""
    # Using the tanh approximation for better performance
    # GELU(x) ≈ 0.5 * x * (1 + tanh(sqrt(2/π) * (x + 0.044715 * x^3)))
    sqrt_2_over_pi = 0.7978845608028654
    tanh_coeff = 0.044715
    x_cubed = x * x * x
    inner = sqrt_2_over_pi * (x + tanh_coeff * x_cubed)
    tanh_value = tl.tanh(inner)
    return 0.5 * x * (1.0 + tanh_value)

@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Out_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om, stride_on,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    USE_ACCUM_FP32: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_remaining = K - k
        k_mask = offs_k < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask[None, :] & (offs_m[:, None] < M), other=0.0)
        w = tl.load(W_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        
        if USE_ACCUM_FP32:
            x = x.to(tl.float32)
            w = w.to(tl.float32)
        
        accumulator += tl.dot(x, w)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk
    
    B_ptrs = B_ptr + offs_n
    bias = tl.load(B_ptrs, mask=offs_n < N, other=0.0)
    bias = bias.to(tl.float32)
    
    accumulator += bias[None, :]
    
    output = _gelu_activation(accumulator)
    output = output.to(tl.float16)
    
    offs_out_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_out_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    Out_ptrs = Out_ptr + offs_out_m[:, None] * stride_om + offs_out_n[None, :] * stride_on
    
    out_mask = (offs_out_m[:, None] < M) & (offs_out_n[None, :] < N)
    tl.store(Out_ptrs, output, mask=out_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X{K} vs W{K_check}"
    assert B.shape == (N,), f"Bias shape mismatch: {B.shape} vs ({N},)"
    
    out = torch.empty((M, N), dtype=torch.float16, device=X.device)
    
    if M == 512 and N == 4096 and K == 4096:
        # Optimized config for M=512
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 256
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 4
    elif M == 1024 and N == 4096 and K == 4096:
        # Optimized config for M=1024
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 256
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 8
    else:
        # Generic fallback configuration
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 256
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 8
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),
    )
    
    _linear_gelu_kernel[grid](
        X, W, B, out,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        out.stride(0), out.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        USE_ACCUM_FP32=True,
        GROUP_SIZE_M=GROUP_SIZE_M
    )
    
    return out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
import math

@triton.jit
def _gelu_activation(x):
    """Fast approximation of GELU activation."""
    sqrt_2_over_pi = 0.7978845608028654
    tanh_coeff = 0.044715
    x_cubed = x * x * x
    inner = sqrt_2_over_pi * (x + tanh_coeff * x_cubed)
    tanh_value = tl.tanh(inner)
    return 0.5 * x * (1.0 + tanh_value)

@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Out_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om, stride_on,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    USE_ACCUM_FP32: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_remaining = K - k
        k_mask = offs_k < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask[None, :] & (offs_m[:, None] < M), other=0.0)
        w = tl.load(W_ptrs, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)
        
        if USE_ACCUM_FP32:
            x = x.to(tl.float32)
            w = w.to(tl.float32)
        
        accumulator += tl.dot(x, w)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk
    
    B_ptrs = B_ptr + offs_n
    bias = tl.load(B_ptrs, mask=offs_n < N, other=0.0)
    bias = bias.to(tl.float32)
    
    accumulator += bias[None, :]
    
    output = _gelu_activation(accumulator)
    output = output.to(tl.float16)
    
    offs_out_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_out_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    Out_ptrs = Out_ptr + offs_out_m[:, None] * stride_om + offs_out_n[None, :] * stride_on
    
    out_mask = (offs_out_m[:, None] < M) & (offs_out_n[None, :] < N)
    tl.store(Out_ptrs, output, mask=out_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X{K} vs W{K_check}"
    assert B.shape == (N,), f"Bias shape mismatch: {B.shape} vs ({N},)"
    
    out = torch.empty((M, N), dtype=torch.float16, device=X.device)
    
    if M == 512 and N == 4096 and K == 4096:
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 256
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 4
    elif M == 1024 and N == 4096 and K == 4096:
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 256
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 8
    else:
        BLOCK_SIZE_M = 128
        BLOCK_SIZE_N = 256
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 8
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),
    )
    
    _linear_gelu_kernel[grid](
        X, W, B, out,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        out.stride(0), out.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        USE_ACCUM_FP32=True,
        GROUP_SIZE_M=GROUP_SIZE_M
    )
    
    return out
'''
        return {"code": code}
