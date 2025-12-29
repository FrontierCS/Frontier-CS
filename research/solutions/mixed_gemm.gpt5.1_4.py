import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        k_offsets = k + offs_k

        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + k_offsets[None, :] * stride_xk)
        w_ptrs = W_ptr + (k_offsets[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        x_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
        w_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)

        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w, out_dtype=tl.float32)

    # Add bias
    bias_ptrs = B_ptr + offs_n
    bias = tl.load(bias_ptrs, mask=offs_n < N, other=0.0)
    acc += bias[None, :]

    # GELU using erf approximation:
    # gelu(x) = x * 0.5 * (1 + erf(x / sqrt(2)))
    # erf(x) ≈ sign(x) * sqrt(1 - exp(-x^2 * (4/pi + a*x^2) / (1 + a*x^2)))
    sqrt_half = 0.7071067811865476  # 1 / sqrt(2)
    a = 0.147
    inv_pi = 0.3183098861837907  # 1/pi
    four_over_pi = 4.0 * inv_pi

    x_val = acc
    z = x_val * sqrt_half
    z2 = z * z
    t = 1.0 + a * z2
    exp_arg = -z2 * (four_over_pi + a * z2) / t
    exp_term = tl.exp(exp_arg)
    tmp = 1.0 - exp_term
    one_minus_exp = tl.where(tmp > 0.0, tmp, 0.0)
    sqrt_term = tl.sqrt(one_minus_exp)
    sign_z = tl.where(z >= 0.0, 1.0, -1.0)
    erf_approx = sign_z * sqrt_term

    y = x_val * 0.5 * (1.0 + erf_approx)

    y = y.to(tl.float16)

    y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, y, mask=mask)


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
    if not X.is_cuda or not W.is_cuda or not B.is_cuda:
        raise ValueError("All inputs must be CUDA tensors")

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W.dtype != torch.float16:
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)

    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
        raise ValueError("Expected X: (M, K), W: (K, N), B: (N,)")

    M, K = X.shape
    Kw, N = W.shape
    if Kw != K:
        raise ValueError(f"Incompatible shapes: X is ({M}, {K}), W is ({Kw}, {N})")

    if B.numel() != N:
        raise ValueError(f"Bias must have shape ({N},), got {tuple(B.shape)}")

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

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
        num_warps=8,
        num_stages=3,
    )

    return Y
'''
        return {"code": code}