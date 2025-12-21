import os
import tempfile

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _linear_bias_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    X_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    k = 0
    while k < K:
        k_mask_a = (offs_m[:, None] < M) & (offs_k[None, :] + k < K)
        k_mask_b = (offs_k[:, None] + k < K) & (offs_n[None, :] < N)
        a = tl.load(X_ptrs, mask=k_mask_a, other=0.0)
        b = tl.load(W_ptrs, mask=k_mask_b, other=0.0)
        acc += tl.dot(a, b)
        k += BLOCK_K
        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc = acc + bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    # Prefer tl.math.erf if available; otherwise fall back to tanh approximation for compatibility.
    try:
        erf_vals = tl.math.erf(acc * inv_sqrt2)
        out = 0.5 * acc * (1.0 + erf_vals)
    except AttributeError:
        c = 0.7978845608028654  # sqrt(2/pi)
        y = acc * (1.0 + 0.044715 * acc * acc)
        out = 0.5 * acc * (1.0 + tl.tanh(c * y))

    out_fp16 = out.to(tl.float16)

    Y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptrs, out_fp16, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.

    Args:
        X: (M, K) float16
        W: (K, N) float16
        B: (N,) float32

    Returns:
        (M, N) float16
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All inputs must be on CUDA"
    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "Bias B must be float32"
    assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1, "Invalid input ranks"
    M, Kx = X.shape
    Kw, N = W.shape
    assert Kx == Kw, "K dimension mismatch"
    assert B.numel() == N, "Bias shape mismatch"

    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))
    _linear_bias_gelu_kernel[grid](
        X, W, B, Y,
        M, N, Kx,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
    )
    return Y
'''
        return {"code": code}
