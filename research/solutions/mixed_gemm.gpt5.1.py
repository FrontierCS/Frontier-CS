import torch
import triton
import triton.language as tl


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
    offs_k = tl.arange(0, BLOCK_K)

    mask_m = offs_m < M
    mask_n = offs_n < N

    # Pointers for the first K-tile
    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over K dimension
    for k0 in range(0, K, BLOCK_K):
        k_mask = (k0 + offs_k) < K

        x_mask = mask_m[:, None] & k_mask[None, :]
        w_mask = k_mask[:, None] & mask_n[None, :]

        x = tl.load(x_ptrs + k0 * stride_xk, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs + k0 * stride_wk, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

    # Add bias (broadcast over rows)
    b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
    acc += b[None, :]

    # GELU activation (tanh approximation)
    # gelu(x) ≈ 0.5 * x * (1 + tanh(√(2/π) * (x + 0.044715x^3)))
    x_fp32 = acc
    c0 = 0.7978845608028654  # sqrt(2/pi)
    x3 = x_fp32 * x_fp32 * x_fp32
    inner = c0 * (x_fp32 + 0.044715 * x3)
    gelu = 0.5 * x_fp32 * (1.0 + tl.tanh(inner))

    # Store result as float16
    y = gelu.to(tl.float16)
    y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    mask = mask_m[:, None] & mask_n[None, :]
    tl.store(y_ptrs, y, mask=mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes: X(M,K) @ W(K,N)"
    assert B.shape[0] == N, "Bias must have shape (N,)"

    assert X.is_cuda and W.is_cuda and B.is_cuda, "All inputs must be on CUDA device"
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_ym, stride_yn = Y.stride()

    # Simple heuristic for block sizes tuned for 4k x 4k-ish GEMMs
    BLOCK_M = 128 if M >= 128 else 64
    BLOCK_N = 128 if N >= 128 else 64
    BLOCK_K = 32

    grid = (
        triton.cdiv(M, BLOCK_M),
        triton.cdiv(N, BLOCK_N),
    )

    _linear_gelu_kernel[grid](
        X,
        W,
        B,
        Y,
        M,
        N,
        K,
        stride_xm,
        stride_xk,
        stride_wk,
        stride_wn,
        stride_ym,
        stride_yn,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=4,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}