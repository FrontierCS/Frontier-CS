class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def matmul_gelu_kernel(
    X_PTR, W_PTR, B_PTR, O_PTR,
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
    offs_d = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    lo = 0
    hi = K
    while lo < hi:
        offs_k = lo + offs_d
        x_ptr = X_PTR + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
        w_ptr = W_PTR + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)

        x_k = tl.load(x_ptr, mask=x_mask, other=0.0).to(tl.float32)
        w_k = tl.load(w_ptr, mask=w_mask, other=0.0).to(tl.float32)

        acc += tl.dot(x_k, w_k)
        lo += BLOCK_K

    b_ptr = B_PTR + offs_n * stride_b
    b_mask = offs_n < N
    b = tl.load(b_ptr, mask=b_mask, other=0.0f)
    acc += b[None, :]

    scale = 1.0 / tl.sqrt(2.0)
    erf_arg = acc * scale
    erf_val = tl.erf(erf_arg)
    gelu = 0.5 * acc * (1.0 + erf_val)

    o_ptr = O_PTR + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on
    o_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    o = gelu.to(tl.float16)
    tl.store(o_ptr, o, mask=o_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    O = torch.empty((M, N), dtype=torch.float16, device=X.device)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    matmul_gelu_kernel[grid](
        X, W, B, O,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        O.stride(0), O.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=4
    )
    return O
'''
        return {"code": code}
