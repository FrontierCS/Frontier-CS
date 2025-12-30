import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        k_offsets = k + offs_k

        x_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
        w_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)

        x = tl.load(X_ptrs, mask=x_mask, other=0.0)
        w = tl.load(W_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc += bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    x_scaled = acc * inv_sqrt2
    erf_val = tl.libdevice.erf(x_scaled)
    acc = acc * 0.5 * (1.0 + erf_val)

    y = acc.to(tl.float16)

    Y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptrs, y, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.

    Args:
        X: (M, K) float16 CUDA
        W: (K, N) float16 CUDA
        B: (N,)  float32 CUDA

    Returns:
        (M, N) float16 CUDA
    """
    if not X.is_cuda or not W.is_cuda or not B.is_cuda:
        tmp = X.to(torch.float32) @ W.to(torch.float32) + B.to(torch.float32)
        tmp = torch.nn.functional.gelu(tmp)
        return tmp.to(torch.float16)

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes for matmul"
    assert B.numel() == N, "Bias size must match output features"

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W.dtype != torch.float16:
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 32

    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)
    grid = (grid_m * grid_n,)

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
        K=K,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=3,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = '''import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        k_offsets = k + offs_k

        x_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
        w_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)

        x = tl.load(X_ptrs, mask=x_mask, other=0.0)
        w = tl.load(W_ptrs, mask=w_mask, other=0.0)

        acc += tl.dot(x, w)

        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc += bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    x_scaled = acc * inv_sqrt2
    erf_val = tl.libdevice.erf(x_scaled)
    acc = acc * 0.5 * (1.0 + erf_val)

    y = acc.to(tl.float16)

    Y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(Y_ptrs, y, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.

    Args:
        X: (M, K) float16 CUDA
        W: (K, N) float16 CUDA
        B: (N,)  float32 CUDA

    Returns:
        (M, N) float16 CUDA
    """
    if not X.is_cuda or not W.is_cuda or not B.is_cuda:
        tmp = X.to(torch.float32) @ W.to(torch.float32) + B.to(torch.float32)
        tmp = torch.nn.functional.gelu(tmp)
        return tmp.to(torch.float16)

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes for matmul"
    assert B.numel() == N, "Bias size must match output features"

    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W.dtype != torch.float16:
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 32

    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)
    grid = (grid_m * grid_n,)

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
        K=K,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=3,
    )

    return Y
'''
        return {"code": kernel_code}