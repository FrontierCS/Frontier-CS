class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def linear_gelu_kernel(
    X_PTR, W_PTR, B_PTR, OUT_PTR,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_xm: tl.int32, stride_xk: tl.int32,
    stride_wk: tl.int32, stride_wn: tl.int32,
    stride_b: tl.int32,
    stride_outm: tl.int32, stride_outn: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    block_k = tl.arange(0, BLOCK_K)
    offs_m = pid_m * BLOCK_M + block_m
    offs_n = pid_n * BLOCK_N + block_n
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        cur_k = start_k + block_k
        x_ptrs = X_PTR + (offs_m[:, None] * stride_xm + cur_k[None, :] * stride_xk)
        x_mask = (offs_m[:, None] < M) & (cur_k[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w_ptrs = W_PTR + (cur_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
        w_mask = (cur_k[:, None] < K) & (offs_n[None, :] < N)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)
        acc += tl.dot(x, w)
    b_ptrs = B_PTR + offs_n * stride_b
    b_mask = offs_n < N
    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
    b = b[None, :]
    acc += b
    sqrt2 = tl.math.sqrt(2.0)
    erf_arg = acc / sqrt2
    erf = tl.extra.cuda.libdevice.erf(erf_arg)
    gelu = acc * 0.5 * (1.0 + erf)
    out_ptrs = OUT_PTR + (offs_m[:, None] * stride_outm + offs_n[None, :] * stride_outn)
    out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    out = gelu.to(tl.float16)
    tl.store(out_ptrs, out, mask=out_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    output = torch.empty((M, N), dtype=torch.float16, device=X.device)
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    linear_gelu_kernel[grid](
        X, W, B, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        output.stride(0), output.stride(1),
    )
    return output
"""
        return {"code": code}