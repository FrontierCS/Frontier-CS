import os
import textwrap

KERNEL_CODE = textwrap.dedent(r'''
import torch
import triton
import triton.language as tl

try:
    _erf = tl.extra.cuda.libdevice.erf
except Exception:
    _erf = tl.math.erf

@triton.jit
def _linear_bias_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M: tl.int32, N: tl.int32,
    stride_xm: tl.int32, stride_xk: tl.int32,
    stride_wk: tl.int32, stride_wn: tl.int32,
    stride_ym: tl.int32, stride_yn: tl.int32,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size_m = GROUP_M
    pid_group = pid // (group_size_m * grid_n)
    first_pid_m = pid_group * group_size_m
    group_size_m = tl.minimum(grid_m - first_pid_m, group_size_m)
    pid_in_group = pid % (group_size_m * grid_n)
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    tl.multiple_of(stride_xk, 1)
    tl.multiple_of(stride_wn, 1)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    x_row_ptrs = X_ptr + rm[:, None] * stride_xm
    w_col_ptrs = W_ptr + rn[None, :] * stride_wn

    rk = tl.arange(0, BLOCK_K)
    for k0 in tl.static_range(0, K, BLOCK_K):
        k = k0 + rk
        a_ptrs = x_row_ptrs + k[None, :] * stride_xk
        b_ptrs = w_col_ptrs + k[:, None] * stride_wk

        a = tl.load(a_ptrs, mask=(rm[:, None] < M) & (k[None, :] < K), other=0.0).to(tl.float16)
        b = tl.load(b_ptrs, mask=(k[:, None] < K) & (rn[None, :] < N), other=0.0, cache_modifier=".ca").to(tl.float16)

        acc += tl.dot(a, b)

    bias = tl.load(B_ptr + rn, mask=(rn < N), other=0.0).to(tl.float32)
    x = acc + bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    y = 0.5 * x * (1.0 + _erf(x * inv_sqrt2))

    y = y.to(tl.float16)
    out_ptrs = Y_ptr + rm[:, None] * stride_ym + rn[None, :] * stride_yn
    tl.store(out_ptrs, y, mask=(rm[:, None] < M) & (rn[None, :] < N))


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not X.is_cuda or not W.is_cuda or not B.is_cuda:
        raise ValueError("All inputs must be CUDA tensors.")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be torch.float16.")
    if B.dtype != torch.float32:
        raise ValueError("B must be torch.float32.")
    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
        raise ValueError("Invalid ranks: X (2D), W (2D), B (1D).")
    M, K = X.shape
    KW, N = W.shape
    if KW != K:
        raise ValueError(f"Shape mismatch: X is (M={M}, K={K}) but W is (K={KW}, N={N}).")
    if B.shape[0] != N:
        raise ValueError(f"Shape mismatch: B is (N={B.shape[0]}) but W has N={N}.")

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    GROUP_M = 8

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    _linear_bias_gelu_kernel[grid](
        X, W, B, Y,
        M, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
        K=K,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        num_warps=8,
        num_stages=4,
    )
    return Y
''').strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}