import torch
import triton
import triton.language as tl

@triton.jit
def linear_gelu_kernel(
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
    block_m = pid_m * BLOCK_M
    block_n = pid_n * BLOCK_N

    offs_m = block_m + tl.arange(0, BLOCK_M)
    offs_n = block_n + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for start_k in range(0, K, BLOCK_K):
        offs_k_start = start_k + offs_k

        x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k_start[None, :] * stride_xk
        x_mask = (offs_m[:, None] < M) & (offs_k_start[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)

        w_ptrs = W_ptr + offs_k_start[:, None] * stride_wk + offs_n[None, :] * stride_wn
        w_mask = (offs_k_start[:, None] < K) & (offs_n[None, :] < N)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

    b_ptrs = B_ptr + offs_n * stride_b
    b_mask = offs_n < N
    b = tl.load(b_ptrs, mask=b_mask, other=tl.float32(0.0))
    acc += b[None, :]

    scale = tl.math.sqrt(tl.float32(0.5))
    erf_vals = tl.extra.cuda.libdevice.erf(acc * scale)
    gelu = acc * 0.5 * (tl.float32(1.0) + erf_vals)

    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    y = gelu.to(tl.float16)
    tl.store(y_ptrs, y, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    assert K == W.shape[0]
    assert B.shape[0] == N
    assert X.is_cuda and W.is_cuda and B.is_cuda
    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)

    if M == 0 or N == 0 or K == 0:
        return Y

    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_wk = W.stride(0)
    stride_wn = W.stride(1)
    stride_b = B.stride(0)
    stride_ym = Y.stride(0)
    stride_yn = Y.stride(1)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_ym, stride_yn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def linear_gelu_kernel(
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
    block_m = pid_m * BLOCK_M
    block_n = pid_n * BLOCK_N

    offs_m = block_m + tl.arange(0, BLOCK_M)
    offs_n = block_n + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for start_k in range(0, K, BLOCK_K):
        offs_k_start = start_k + offs_k

        x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k_start[None, :] * stride_xk
        x_mask = (offs_m[:, None] < M) & (offs_k_start[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)

        w_ptrs = W_ptr + offs_k_start[:, None] * stride_wk + offs_n[None, :] * stride_wn
        w_mask = (offs_k_start[:, None] < K) & (offs_n[None, :] < N)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

    b_ptrs = B_ptr + offs_n * stride_b
    b_mask = offs_n < N
    b = tl.load(b_ptrs, mask=b_mask, other=tl.float32(0.0))
    acc += b[None, :]

    scale = tl.math.sqrt(tl.float32(0.5))
    erf_vals = tl.extra.cuda.libdevice.erf(acc * scale)
    gelu = acc * 0.5 * (tl.float32(1.0) + erf_vals)

    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    y = gelu.to(tl.float16)
    tl.store(y_ptrs, y, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    assert K == W.shape[0]
    assert B.shape[0] == N
    assert X.is_cuda and W.is_cuda and B.is_cuda
    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)

    if M == 0 or N == 0 or K == 0:
        return Y

    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_wk = W.stride(0)
    stride_wn = W.stride(1)
    stride_b = B.stride(0)
    stride_ym = Y.stride(0)
    stride_yn = Y.stride(1)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_ym, stride_yn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )
    return Y
"""
        return {"code": code}
