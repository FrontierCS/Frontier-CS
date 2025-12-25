class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

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
    M, K = X.shape
    _, N = W.shape
    output = torch.empty((M, N), dtype=torch.float16, device=X.device)
    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 64

    @triton.jit
    def kernel(
        X_ptr, W_ptr, B_ptr, output_ptr,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_om, stride_on,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        k = 0
        while k < K:
            offs_k = k + tl.arange(0, BLOCK_K)
            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
            x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
            x = tl.load(x_ptrs, mask=x_mask, other=0.0)
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0)
            acc += tl.dot(x.to(tl.float32), w.to(tl.float32))
            k += BLOCK_K
        b_ptrs = B_ptr + offs_n * stride_b
        b_mask = offs_n < N
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += b[None, :]
        gelu = acc * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(acc * 0.70710678118654757))
        o = gelu.to(tl.float16)
        out_ptrs = output_ptr + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on
        out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(out_ptrs, o, mask=out_mask)

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    kernel[grid](
        X, W, B, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        output.stride(0), output.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=1,
        num_warps=4
    )
    return output
"""
        return {"code": code}
