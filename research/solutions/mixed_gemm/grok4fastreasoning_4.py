import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def matmul_with_bias_gelu_kernel(
    X_PTR, W_PTR, B_PTR, Y_PTR,
    M, N, K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k_start in range(0, K, BLOCK_K):
        x_ptr = tl.make_block_ptr(
            base=X_PTR,
            shape=(M, K),
            strides=(X_PTR.stride(0), X_PTR.stride(1)),
            offset=(pid_m * BLOCK_M, k_start),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(0, 1)
        )
        w_ptr = tl.make_block_ptr(
            base=W_PTR,
            shape=(K, N),
            strides=(W_PTR.stride(0), W_PTR.stride(1)),
            offset=(k_start, pid_n * BLOCK_N),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        x_mask = (offs_m[:, None] < M) & ((k_start + tl.arange(0, BLOCK_K))[None, :] < K)
        w_mask = ((k_start + tl.arange(0, BLOCK_K))[:, None] < K) & (offs_n[None, :] < N)
        x = tl.load(x_ptr, mask=x_mask, other=0.0).to(tl.float32)
        w = tl.load(w_ptr, mask=w_mask, other=0.0).to(tl.float32)
        acc += tl.dot(x, w)
    b_offsets = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    b_mask = b_offsets < N
    b_ptrs = B_PTR + b_offsets
    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
    acc += b[None, :]
    def gelu(x):
        return x * 0.5 * (1.0 + tl.libdevice.erf(x * 0.7071067811865476))
    o = gelu(acc)
    o_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    o_fp16 = o.to(tl.float16)
    y_ptr = tl.make_block_ptr(
        base=Y_PTR,
        shape=(M, N),
        strides=(Y_PTR.stride(0), Y_PTR.stride(1)),
        offset=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(0, 1)
    )
    tl.store(y_ptr, o_fp16, mask=o_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    Y = torch.empty((M, N), dtype=torch.float16, device=X.device, memory_format=torch.contiguous_format)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    matmul_with_bias_gelu_kernel[grid](
        X, W, B, Y, M, N, K,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )
    return Y
"""
        return {"code": code}