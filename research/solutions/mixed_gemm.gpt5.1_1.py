import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, O_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om, stride_on,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        offs_k = k + tl.arange(0, BLOCK_K)

        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)

        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)
    acc += bias[None, :]

    x_val = acc
    x_cube = x_val * x_val * x_val
    sqrt_2_over_pi = 0.7978845608028654
    inner = sqrt_2_over_pi * (x_val + 0.044715 * x_cube)
    two_inner = 2.0 * inner
    e = tl.exp(two_inner)
    tanh_inner = (e - 1.0) / (e + 1.0)
    gelu = 0.5 * x_val * (1.0 + tanh_inner)

    o_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_n[None, :] * stride_on)
    o_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(o_ptrs, gelu.to(tl.float16), mask=o_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if X.device.type != 'cuda' or W.device.type != 'cuda' or B.device.type != 'cuda':
        raise ValueError("All inputs must be CUDA tensors.")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be float16 tensors.")
    if B.dtype != torch.float32:
        raise ValueError("B must be a float32 tensor.")
    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
        raise ValueError("Shapes must be X: (M, K), W: (K, N), B: (N,)")

    M, K = X.shape
    K_w, N = W.shape
    if K_w != K:
        raise ValueError("Incompatible shapes: X is (M, K) and W is (K_w, N) with K_w != K.")
    if B.shape[0] != N:
        raise ValueError("Bias shape must be (N,)")

    O = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_om, stride_on = O.stride()

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )

    _linear_gelu_kernel[grid](
        X, W, B, O,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_om, stride_on,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
