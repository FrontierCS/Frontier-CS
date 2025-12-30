import os
import math
import torch
import triton
import triton.language as tl

try:
    from triton.language.extra.cuda import libdevice as _libdevice

    @tl.inline
    def _tl_erf(x):
        return _libdevice.erf(x)
except Exception:
    try:
        @tl.inline
        def _tl_erf(x):
            return tl.math.erf(x)
    except Exception:
        @tl.inline
        def _tl_erf(x):
            # Abramowitz and Stegun approximation for erf
            # erf(x) ≈ sign(x) * (1 - (((((a5 t + a4) t + a3) t + a2) t + a1) t) * exp(-x^2))
            # where t = 1 / (1 + p|x|)
            p = 0.3275911
            a1 = 0.254829592
            a2 = -0.284496736
            a3 = 1.421413741
            a4 = -1.453152027
            a5 = 1.061405429
            ax = tl.abs(x)
            t = 1.0 / (1.0 + p * ax)
            y = (((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t)
            y = 1.0 - y * tl.exp(-(ax * ax))
            return tl.where(x >= 0, y, -y)


@triton.autotune(
    configs=[
        triton.Config({"BM": 128, "BN": 128, "BK": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BM": 128, "BN": 128, "BK": 64, "GROUP_M": 8}, num_warps=8, num_stages=3),
        triton.Config({"BM": 64, "BN": 128, "BK": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BM": 64, "BN": 128, "BK": 64, "GROUP_M": 8}, num_warps=4, num_stages=3),
        triton.Config({"BM": 128, "BN": 64, "BK": 32, "GROUP_M": 8}, num_warps=4, num_stages=5),
        triton.Config({"BM": 64, "BN": 64, "BK": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _linear_gelu_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    Y_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_xm,
    stride_xk,
    stride_wk,
    stride_wn,
    stride_ym,
    stride_yn,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BK: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BM)
    num_pid_n = tl.cdiv(N, BN)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    offs_k = tl.arange(0, BK)

    acc = tl.zeros((BM, BN), dtype=tl.float32)

    tl.multiple_of(stride_xk, 8)
    tl.multiple_of(stride_wn, 8)
    tl.multiple_of(K, BK)

    for k0 in tl.static_range(0, K, BK):
        k = k0 + offs_k
        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + k[None, :] * stride_xk)
        b_ptrs = W_ptr + (k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (k[None, :] < K), other=0.0).to(tl.float16)
        b = tl.load(b_ptrs, mask=(k[:, None] < K) & (offs_n[None, :] < N), other=0.0).to(tl.float16)
        acc += tl.dot(a, b, out_dtype=tl.float32)

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    x = acc + bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    y = x * 0.5 * (1.0 + _tl_erf(x * inv_sqrt2))
    y = y.to(tl.float16)

    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    tl.store(y_ptrs, y, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be float16")
    if B.dtype != torch.float32:
        raise ValueError("B must be float32")
    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
        raise ValueError("Expected X: (M,K), W: (K,N), B: (N,)")

    M, K = X.shape
    Kw, N = W.shape
    if Kw != K or B.shape[0] != N:
        raise ValueError("Shape mismatch")

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_ym, stride_yn = Y.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BM"]) * triton.cdiv(N, meta["BN"]),)
    _linear_gelu_kernel[grid](
        X,
        W,
        B,
        Y,
        M=M,
        N=N,
        K=K,
        stride_xm=stride_xm,
        stride_xk=stride_xk,
        stride_wk=stride_wk,
        stride_wn=stride_wn,
        stride_ym=stride_ym,
        stride_yn=stride_yn,
    )
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}