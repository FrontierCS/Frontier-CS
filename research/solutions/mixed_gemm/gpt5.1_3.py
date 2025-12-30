import os
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        offs_k = k + tl.arange(0, BLOCK_K)

        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        x_mask = (mask_m[:, None]) & (offs_k[None, :] < K)
        w_mask = (offs_k[:, None] < K) & (mask_n[None, :])

        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w, out_dtype=tl.float32)

    b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
    acc += b[None, :]

    sqrt_2_over_pi = 0.7978845608028654
    gelu_const = 0.044715

    x_val = acc
    x_cubed = x_val * x_val * x_val
    inner = sqrt_2_over_pi * (x_val + gelu_const * x_cubed)
    gelu = 0.5 * x_val * (1.0 + tl.tanh(inner))

    y = gelu.to(tl.float16)

    y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    tl.store(y_ptrs, y, mask=mask_m[:, None] & mask_n[None, :])


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if (not X.is_cuda) or (not W.is_cuda) or (not B.is_cuda) or (not torch.cuda.is_available()):
        X32 = X.to(torch.float32)
        W32 = W.to(torch.float32)
        B32 = B.to(torch.float32)
        out = X32 @ W32 + B32
        out = torch.nn.functional.gelu(out, approximate="tanh")
        return out.to(torch.float16)

    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All tensors must be CUDA tensors"

    M, K = X.shape
    K_w, N = W.shape
    assert K == K_w, "Incompatible matrix dimensions"
    assert B.shape[0] == N, "Bias dimension must match output features"

    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 32

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=4,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        program_path = inspect.getsourcefile(Solution)
        if program_path is None:
            program_path = os.path.abspath(__file__)
        else:
            program_path = os.path.abspath(program_path)
        return {"program_path": program_path}