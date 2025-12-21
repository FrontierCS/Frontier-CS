import torch
import triton
import triton.language as tl
import math

@triton.jit
def fast_gelu(x):
    """Fast approximation of GELU activation."""
    return x * 0.5 * (1.0 + tl.tanh(0.7978845608 * (x + 0.044715 * x * x * x)))

@triton.jit
def accurate_gelu(x):
    """Accurate GELU using erf function."""
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def linear_gelu_kernel(
    x_ptr, w_ptr, b_ptr, out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_outm, stride_outn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr = 8,
    ACC_TYPE: tl.constexpr = tl.float32,
    USE_FAST_GELU: tl.constexpr = True
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
    
    x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = w_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = K - k
        k_size = min(BLOCK_K, k_remaining)
        
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < k_size)
        w_mask = (offs_k[:, None] < k_size) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)
        
        accumulator += tl.dot(x, w, out_dtype=ACC_TYPE)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    if b_ptr is not None:
        b_ptrs = b_ptr + offs_n
        b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        accumulator += b[None, :]
    
    if USE_FAST_GELU:
        output = fast_gelu(accumulator)
    else:
        output = accurate_gelu(accumulator)
    
    out_ptrs = out_ptr + (offs_m[:, None] * stride_outm + offs_n[None, :] * stride_outn)
    out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(out_ptrs, output.to(tl.float16), mask=out_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K, N = W.shape
    
    out = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    def get_config(M, N, K):
        if M <= 512 and N <= 512:
            return (64, 64, 32, 4, 8, True)
        elif M >= 1024 and N >= 1024:
            return (128, 128, 64, 8, 4, False)
        else:
            return (128, 256, 32, 4, 4, True)
    
    BLOCK_M, BLOCK_N, BLOCK_K, num_stages, num_warps, use_fast_gelu = get_config(M, N, K)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    linear_gelu_kernel[grid](
        X, W, B, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0) if B.ndim > 0 else 0,
        out.stride(0), out.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        GROUP_M=8,
        num_stages=num_stages,
        num_warps=num_warps,
        USE_FAST_GELU=use_fast_gelu
    )
    
    return out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__("inspect").getsource(__import__(__name__))}
