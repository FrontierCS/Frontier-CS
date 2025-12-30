import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_bias_gelu_f16_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_mask = k0 + offs_k < K
        m_mask = offs_m < M
        n_mask = offs_n < N

        x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0).to(tl.float16)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float16)

        acc += tl.dot(x, w, out_dtype=tl.float32)

        k0 += BLOCK_K
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    # Add bias
    b = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc = acc + b[None, :]

    # GELU approximation (tanh-based)
    sqrt_2_over_pi = 0.7978845608028654  # sqrt(2/pi)
    c = acc + 0.044715 * acc * acc * acc
    c = sqrt_2_over_pi * c
    y = 0.5 * acc * (1.0 + tl.tanh(c))

    # Store results
    y = y.to(tl.float16)
    y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    out_mask = (offs_m < M)[:, None] & (offs_n < N)[None, :]
    tl.store(y_ptrs, y, mask=out_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and W.dtype == torch.float16 and B.dtype == torch.float32, "Dtypes must be X:fp16, W:fp16, B:fp32"
    assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1, "Shapes must be X:(M,K), W:(K,N), B:(N,)"

    M, Kx = X.shape
    K, N = W.shape
    assert Kx == K and B.numel() == N, "Incompatible shapes"

    Xc = X.contiguous()
    Wc = W.contiguous()
    Bc = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
    _linear_bias_gelu_f16_kernel[grid](
        Xc, Wc, Bc, Y,
        M, N, K,
        Xc.stride(0), Xc.stride(1),
        Wc.stride(0), Wc.stride(1),
        Y.stride(0), Y.stride(1),
    )
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_bias_gelu_f16_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_mask = k0 + offs_k < K
        m_mask = offs_m < M
        n_mask = offs_n < N

        x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0).to(tl.float16)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float16)

        acc += tl.dot(x, w, out_dtype=tl.float32)

        k0 += BLOCK_K
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    # Add bias
    b = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc = acc + b[None, :]

    # GELU approximation (tanh-based)
    sqrt_2_over_pi = 0.7978845608028654  # sqrt(2/pi)
    c = acc + 0.044715 * acc * acc * acc
    c = sqrt_2_over_pi * c
    y = 0.5 * acc * (1.0 + tl.tanh(c))

    # Store results
    y = y.to(tl.float16)
    y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    out_mask = (offs_m < M)[:, None] & (offs_n < N)[None, :]
    tl.store(y_ptrs, y, mask=out_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and W.dtype == torch.float16 and B.dtype == torch.float32, "Dtypes must be X:fp16, W:fp16, B:fp32"
    assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1, "Shapes must be X:(M,K), W:(K,N), B:(N,)"

    M, Kx = X.shape
    K, N = W.shape
    assert Kx == K and B.numel() == N, "Incompatible shapes"

    Xc = X.contiguous()
    Wc = W.contiguous()
    Bc = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
    _linear_bias_gelu_f16_kernel[grid](
        Xc, Wc, Bc, Y,
        M, N, K,
        Xc.stride(0), Xc.stride(1),
        Wc.stride(0), Wc.stride(1),
        Y.stride(0), Y.stride(1),
    )
    return Y
'''
        return {"code": code}