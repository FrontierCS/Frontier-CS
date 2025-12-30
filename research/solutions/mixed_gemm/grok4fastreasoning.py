class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def kernel_linear_gelu(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    block_k = tl.arange(0, BLOCK_K)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for start_k in range(0, K, BLOCK_K):
        offs_k = start_k + block_k
        
        x_ptr = X_ptr + (pid_m * BLOCK_M + block_m)[:, None] * stride_xm + offs_k[None, :] * stride_xk
        x_mask = ((pid_m * BLOCK_M + block_m)[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(x_ptr, mask=x_mask, other=0.0)
        
        w_ptr = W_ptr + offs_k[:, None] * stride_wk + (pid_n * BLOCK_N + block_n)[None, :] * stride_wn
        w_mask = (offs_k[:, None] < K) & ((pid_n * BLOCK_N + block_n)[None, :] < N)
        w = tl.load(w_ptr, mask=w_mask, other=0.0)
        
        acc += tl.dot(x, w)
    
    b_ptr = B_ptr + (pid_n * BLOCK_N + block_n) * stride_b
    b_mask = (pid_n * BLOCK_N + block_n) < N
    b = tl.load(b_ptr, mask=b_mask, other=0.0)
    b = b[None, :]
    
    acc += b
    
    scale = 0.7071067811865476
    erf_val = tl.math.erf(acc * scale)
    gelu = acc * 0.5 * (1.0 + erf_val)
    
    y_ptr = Y_ptr + (pid_m * BLOCK_M + block_m)[:, None] * stride_ym + (pid_n * BLOCK_N + block_n)[None, :] * stride_yn
    y_mask = ((pid_m * BLOCK_M + block_m)[:, None] < M) & ((pid_n * BLOCK_N + block_n)[None, :] < N)
    tl.store(y_ptr, gelu.to(tl.float16), mask=y_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, Kx = X.shape
    Kw, N = W.shape
    assert Kx == Kw
    K = Kx
    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)
    
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    kernel_linear_gelu[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=4,
        num_warps=8
    )
    
    return Y
"""
        return {"code": code}