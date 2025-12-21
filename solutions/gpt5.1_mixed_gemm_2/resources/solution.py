import torch
import triton
import triton.language as tl

KERNEL_CODE = '''import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_stages=4, num_warps=8),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32}, num_stages=4, num_warps=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32}, num_stages=4, num_warps=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 32}, num_stages=3, num_warps=4),
    ],
    key=["M", "N"],
)
@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_ym, stride_yn,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    for k in range(0, K, BLOCK_K):
        k_valid = offs_k[None, :] + k < K

        x_mask = (offs_m[:, None] < M) & k_valid
        w_mask = k_valid & (offs_n[None, :] < N)

        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    bias = tl.load(B_ptr + offs_n * stride_b, mask=offs_n < N, other=0.0)
    acc += bias[None, :]

    x = acc

    inv_sqrt2 = 0.7071067811865476
    x_scaled = x * inv_sqrt2

    one = 1.0
    minus_one = -1.0
    sign = tl.where(x_scaled >= 0, one, minus_one)
    abs_x = tl.where(x_scaled >= 0, x_scaled, -x_scaled)

    p = 0.3275911
    t = 1.0 / (1.0 + p * abs_x)

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429

    poly = a5 * t + a4
    poly = poly * t + a3
    poly = poly * t + a2
    poly = poly * t + a1
    poly = poly * t

    exp_term = tl.exp(-abs_x * abs_x)
    erf_approx = sign * (1.0 - poly * exp_term)

    y = 0.5 * x * (1.0 + erf_approx)

    y = y.to(tl.float16)

    y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, y, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W.dtype != torch.float16:
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)

    M, K = X.shape
    K_w, N = W.shape
    if K_w != K:
        raise ValueError(f"Incompatible shapes: X is (M={M}, K={K}), W is (K_w={K_w}, N={N})")
    if B.numel() != N:
        raise ValueError(f"Bias must have shape ({N},), got {tuple(B.shape)}")

    X = X.contiguous()
    W = W.contiguous()
    B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_b = B.stride(0)
    stride_ym, stride_yn = Y.stride()

    grid = lambda meta: (
        triton.cdiv(M, meta["BLOCK_M"]),
        triton.cdiv(N, meta["BLOCK_N"]),
    )

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_ym, stride_yn,
        K=K,
    )

    return Y
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
