import torch
import triton
import triton.language as tl

@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    ACC_TYPE: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    pid_m = pid // grid_n
    pid_n = pid % grid_n
    
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    
    if GROUP_M > 1:
        group_id = pid_m // GROUP_M
        first_pid_m = group_id * GROUP_M
        group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
        pid_m = first_pid_m + (pid % group_size_m)
        pid_n = (pid % num_pid_n) + ((pid // group_size_m) * group_size_m)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    B_ptrs = B_ptr + offs_n * stride_bn
    Y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_remaining = K - k * BLOCK_K
        k_effective = min(BLOCK_K, k_remaining)
        
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < k_effective)
        w_mask = (offs_k[:, None] < k_effective) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptrs, mask=x_mask, other=0.0)
        w = tl.load(W_ptrs, mask=w_mask, other=0.0)
        
        acc += tl.dot(x, w)
        
        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk
    
    m_mask = offs_m[:, None] < M
    n_mask = offs_n[None, :] < N
    mask = m_mask & n_mask
    
    b = tl.load(B_ptrs, mask=offs_n < N, other=0.0)
    acc = acc + b[None, :]
    
    acc = acc.to(tl.float32)
    
    GELU_SCALING = 0.7071067811865476
    gelu = acc * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(acc * GELU_SCALING))
    
    gelu = gelu.to(tl.float16)
    tl.store(Y_ptrs, gelu, mask=mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X.shape={X.shape}, W.shape={W.shape}"
    assert B.shape[0] == N, f"Bias shape mismatch: B.shape={B.shape}, expected ({N},)"
    
    Y = torch.empty((M, N), device=X.device, dtype=X.dtype)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_K = 32
    GROUP_M = 8
    
    def grid(META):
        return (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        ACC_TYPE=tl.float32,
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    ACC_TYPE: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    pid_m = pid // grid_n
    pid_n = pid % grid_n
    
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    
    if GROUP_M > 1:
        group_id = pid_m // GROUP_M
        first_pid_m = group_id * GROUP_M
        group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
        pid_m = first_pid_m + (pid % group_size_m)
        pid_n = (pid % num_pid_n) + ((pid // group_size_m) * group_size_m)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    B_ptrs = B_ptr + offs_n * stride_bn
    Y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_remaining = K - k * BLOCK_K
        k_effective = min(BLOCK_K, k_remaining)
        
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < k_effective)
        w_mask = (offs_k[:, None] < k_effective) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptrs, mask=x_mask, other=0.0)
        w = tl.load(W_ptrs, mask=w_mask, other=0.0)
        
        acc += tl.dot(x, w)
        
        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk
    
    m_mask = offs_m[:, None] < M
    n_mask = offs_n[None, :] < N
    mask = m_mask & n_mask
    
    b = tl.load(B_ptrs, mask=offs_n < N, other=0.0)
    acc = acc + b[None, :]
    
    acc = acc.to(tl.float32)
    
    GELU_SCALING = 0.7071067811865476
    gelu = acc * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(acc * GELU_SCALING))
    
    gelu = gelu.to(tl.float16)
    tl.store(Y_ptrs, gelu, mask=mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X.shape={X.shape}, W.shape={W.shape}"
    assert B.shape[0] == N, f"Bias shape mismatch: B.shape={B.shape}, expected ({N},)"
    
    Y = torch.empty((M, N), device=X.device, dtype=X.dtype)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_K = 32
    GROUP_M = 8
    
    def grid(META):
        return (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        ACC_TYPE=tl.float32,
    )
    
    return Y
'''
        return {"code": code}