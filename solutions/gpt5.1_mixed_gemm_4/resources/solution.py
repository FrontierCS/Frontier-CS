from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        code = '''import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_stages=4,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32},
            num_stages=4,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32},
            num_stages=4,
            num_warps=2,
        ),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    Y_ptr,
    M,
    N,
    K,
    stride_xm,
    stride_xk,
    stride_wk,
    stride_wn,
    stride_ym,
    stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    num_k = tl.cdiv(K, BLOCK_K)
    for k in range(0, num_k):
        offs_k = k * BLOCK_K + tl.arange(0, BLOCK_K)

        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc += bias[None, :]

    # GELU approximation using tanh (fast and sufficiently accurate)
    # gelu(x) ≈ 0.5 * x * (1 + tanh(√(2/π) * (x + 0.044715 * x^3)))
    sqrt_2_over_pi = 0.7978845608028654
    coeff = 0.044715

    x = acc
    x3 = x * x * x
    inner = sqrt_2_over_pi * (x + coeff * x3)
    tanh_inner = tl.tanh(inner)
    acc = 0.5 * x * (1.0 + tanh_inner)

    y = acc.to(tl.float16)

    out_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(out_ptrs, y, mask=out_mask)


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
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All tensors must be on CUDA"
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes for matrix multiplication"
    assert B.shape[0] == N, "Bias must have shape (N,)"

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    _linear_gelu_kernel[grid](
        X,
        W,
        B,
        Y,
        M,
        N,
        K,
        X.stride(0),
        X.stride(1),
        W.stride(0),
        W.stride(1),
        Y.stride(0),
        Y.stride(1),
    )

    return Y
'''
        return {"code": code}
