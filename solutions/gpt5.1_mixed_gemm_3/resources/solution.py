import torch
import torch.nn.functional as F
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_stages=3,
            num_warps=8,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_stages=3,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32},
            num_stages=3,
            num_warps=4,
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
    stride_b,
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
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

    k = 0
    while k < K:
        k_mask = (offs_k[None, :] + k) < K

        x_mask = (offs_m[:, None] < M) & k_mask
        w_mask = k_mask.T & (offs_n[None, :] < N)

        a = tl.load(x_ptrs, mask=x_mask, other=0.0)
        b = tl.load(w_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(a, b)

        k += BLOCK_K
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    mask_m = offs_m < M
    mask_n = offs_n < N

    bias = tl.load(B_ptr + offs_n * stride_b, mask=mask_n, other=0.0)
    bias = bias.to(tl.float32)
    acc = acc + bias[None, :]

    x = acc
    sqrt_2_over_pi = 0.7978845608028654
    c = 0.044715
    x3 = x * x * x
    inner = sqrt_2_over_pi * (x + c * x3)
    y = 0.5 * x * (1.0 + tl.tanh(inner))

    y = y.to(tl.float16)

    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    out_mask = mask_m[:, None] & mask_n[None, :]
    tl.store(y_ptrs, y, mask=out_mask)


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
    if not (X.is_cuda and W.is_cuda and B.is_cuda):
        out = X.to(torch.float32) @ W.to(torch.float32)
        out = out + B.to(torch.float32)
        out = F.gelu(out, approximate='tanh')
        return out.to(torch.float16)

    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype in (torch.float16, torch.float32)

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K
    assert B.numel() == N

    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
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
        B.stride(0),
        Y.stride(0),
        Y.stride(1),
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
