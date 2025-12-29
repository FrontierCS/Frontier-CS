import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    output = torch.empty((M, N), dtype=torch.float16, device=X.device)
    
    @triton.jit
    def kernel(
        X_ptr, W_ptr, B_ptr, Y_ptr,
        M: tl.int32, N: tl.int32, K: tl.int32,
        stride_xm: tl.int32, stride_xk: tl.int32,
        stride_wk: tl.int32, stride_wn: tl.int32,
        stride_b: tl.int32,
        stride_ym: tl.int32, stride_yn: tl.int32,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k_base = tl.arange(0, BLOCK_K)
        
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        
        lo = 0
        while lo < K:
            offs_k = lo + offs_k_base
            
            x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
            w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
            
            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            x = tl.load(x_ptrs, mask=x_mask, other=0.0)
            
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0)
            
            acc += tl.dot(x, w)
            lo += BLOCK_K
        
        b_mask = offs_n < N
        b_ptrs = B_ptr + offs_n * stride_b
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += b[None, :]
        
        inv_sqrt_2 = 0.7071067811865476
        gelu = acc * 0.5 * (1.0 + tl.erf(acc * inv_sqrt_2))
        
        y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
        tl.store(y_ptrs, gelu.to(tl.float16), mask=y_mask)
    
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_wk = W.stride(0)
    stride_wn = W.stride(1)
    stride_b = B.stride(0)
    stride_ym = output.stride(0)
    stride_yn = output.stride(1)
    
    kernel[grid](
        X, W, B, output,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_ym, stride_yn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=4,
        num_warps=8
    )
    
    return output
"""
        return {"code": code}