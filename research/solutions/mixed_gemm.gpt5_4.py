import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = r'''
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 64}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=8, num_stages=5),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _linear_bias_gelu_kernel(
    X_ptr, W_ptr, B_ptr, O_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om, stride_on,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    offs_k = tl.arange(0, BLOCK_K)

    # Accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Pointers increments
    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    k = 0
    while k < K:
        k_mask = offs_k[None, :] + k < K
        x_mask = (offs_m[:, None] < M) & k_mask
        w_mask = k_mask.T & (offs_n[None, :] < N)

        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)

        # Ensure inputs are fp16 for matmul, accumulation in fp32
        x = x.to(tl.float16)
        w = w.to(tl.float16)
        acc += tl.dot(x, w, out_dtype=tl.float32)

        k += BLOCK_K
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    # Add bias
    b = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc = acc + b[None, :]

    # GELU using high-accuracy erf approximation (Abramowitz & Stegun 7.1.26)
    # gelu(x) = 0.5 * x * (1 + erf(x / sqrt(2)))
    inv_sqrt2 = 0.7071067811865476
    z = acc * inv_sqrt2
    az = tl.abs(z)
    t = 1.0 / (1.0 + 0.3275911 * az)
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    poly = (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t
    y = 1.0 - poly * tl.exp(-az * az)
    sign = tl.where(z >= 0, 1.0, -1.0)
    erfz = sign * y
    out = 0.5 * acc * (1.0 + erfz)

    # Store
    o_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_n[None, :] * stride_on)
    out = out.to(tl.float16)
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(o_ptrs, out, mask=mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.

    Args:
        X: (M, K) float16 CUDA
        W: (K, N) float16 CUDA
        B: (N,) float32 CUDA

    Returns:
        (M, N) float16 CUDA
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All inputs must be on CUDA"
    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "Bias B must be float32"
    assert X.shape[1] == W.shape[0], "Inner dimensions must match"
    assert W.shape[1] == B.shape[0], "Bias size must match output features"

    M, K = X.shape
    K2, N = W.shape
    device = X.device

    O = torch.empty((M, N), device=device, dtype=torch.float16)

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))

    _linear_bias_gelu_kernel[grid](
        X, W, B, O,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        O.stride(0), O.stride(1),
    )
    return O
'''
        return {"code": kernel_code}