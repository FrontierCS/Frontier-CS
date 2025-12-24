import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_yn, stride_ym,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        k_remaining = K - k
        k_mask = offs_k[None, :] < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask & (offs_m[:, None] < M), other=0.0).to(tl.float32)
        w = tl.load(W_ptrs, mask=k_mask & (offs_n[None, :] < N), other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w, allow_tf32=False)
        
        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk
    
    bias_ptrs = B_ptr + offs_n
    bias = tl.load(bias_ptrs, mask=offs_n < N, other=0.0)
    acc += bias[None, :]
    
    CONST_SQRT_2_OVER_PI = 0.7978845608028654
    CONST_COEF = 0.044715
    x = acc.to(tl.float32)
    x_cubed = x * x * x
    inner = CONST_SQRT_2_OVER_PI * (x + CONST_COEF * x_cubed)
    tanh_res = tl.tanh(inner)
    gelu = 0.5 * x * (1.0 + tanh_res)
    
    out = gelu.to(tl.float16)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    Y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptrs, out, mask=mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X.shape={X.shape}, W.shape={W.shape}"
    assert B.shape == (N,), f"Bias shape mismatch: B.shape={B.shape}, expected ({N},)"
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(1), Y.stride(0),
    )
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_yn, stride_ym,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        k_remaining = K - k
        k_mask = offs_k[None, :] < k_remaining
        
        x = tl.load(X_ptrs, mask=k_mask & (offs_m[:, None] < M), other=0.0).to(tl.float32)
        w = tl.load(W_ptrs, mask=k_mask & (offs_n[None, :] < N), other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w, allow_tf32=False)
        
        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk
    
    bias_ptrs = B_ptr + offs_n
    bias = tl.load(bias_ptrs, mask=offs_n < N, other=0.0)
    acc += bias[None, :]
    
    CONST_SQRT_2_OVER_PI = 0.7978845608028654
    CONST_COEF = 0.044715
    x = acc.to(tl.float32)
    x_cubed = x * x * x
    inner = CONST_SQRT_2_OVER_PI * (x + CONST_COEF * x_cubed)
    tanh_res = tl.tanh(inner)
    gelu = 0.5 * x * (1.0 + tanh_res)
    
    out = gelu.to(tl.float16)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    Y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptrs, out, mask=mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X.shape={X.shape}, W.shape={W.shape}"
    assert B.shape == (N,), f"Bias shape mismatch: B.shape={B.shape}, expected ({N},)"
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(1), Y.stride(0),
    )
    return Y
'''
        return {"code": code}
