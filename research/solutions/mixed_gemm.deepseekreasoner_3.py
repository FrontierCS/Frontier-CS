import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def linear_gelu_kernel(
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
    stride_bn,
    stride_ym,
    stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    B_ptr += offs_n * stride_bn

    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_remaining = K - k * BLOCK_K
        k_mask = offs_k < k_remaining
        
        x_mask = (offs_m[:, None] < M) & k_mask[None, :]
        x_chunk = tl.load(X_ptr, mask=x_mask, other=0.0).to(tl.float16)
        
        w_mask = k_mask[:, None] & (offs_n[None, :] < N)
        w_chunk = tl.load(W_ptr, mask=w_mask, other=0.0).to(tl.float16)
        
        accumulator += tl.dot(x_chunk, w_chunk, out_dtype=tl.float32)
        
        X_ptr += BLOCK_K * stride_xk
        W_ptr += BLOCK_K * stride_wk

    accumulator = accumulator.to(tl.float32)

    b_mask = offs_n < N
    bias = tl.load(B_ptr, mask=b_mask, other=0.0).to(tl.float32)
    accumulator += bias[None, :]

    GELU_COEF_1 = 0.044715
    GELU_COEF_2 = 0.7978845608028654
    GELU_COEF_3 = 0.5
    x = accumulator
    x_cubed = x * x * x
    inner = GELU_COEF_1 * x_cubed + x
    inner_scaled = inner * GELU_COEF_2
    tanh_inner = tl.math.tanh(inner_scaled)
    gelu = GELU_COEF_3 * x * (1 + tanh_inner)

    output = gelu.to(tl.float16)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, output, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X{K=} != W{K_check=}"
    assert B.shape == (N,), f"Bias shape {B.shape} != (N={N},)"
    assert X.dtype == torch.float16, f"X dtype {X.dtype} != float16"
    assert W.dtype == torch.float16, f"W dtype {W.dtype} != float16"
    assert B.dtype == torch.float32, f"B dtype {B.dtype} != float32"
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    linear_gelu_kernel[grid](
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
        code = """
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=5, num_warps=2),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def linear_gelu_kernel(
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
    stride_bn,
    stride_ym,
    stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    X_ptr += offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptr += offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    B_ptr += offs_n * stride_bn

    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_remaining = K - k * BLOCK_K
        k_mask = offs_k < k_remaining
        
        x_mask = (offs_m[:, None] < M) & k_mask[None, :]
        x_chunk = tl.load(X_ptr, mask=x_mask, other=0.0).to(tl.float16)
        
        w_mask = k_mask[:, None] & (offs_n[None, :] < N)
        w_chunk = tl.load(W_ptr, mask=w_mask, other=0.0).to(tl.float16)
        
        accumulator += tl.dot(x_chunk, w_chunk, out_dtype=tl.float32)
        
        X_ptr += BLOCK_K * stride_xk
        W_ptr += BLOCK_K * stride_wk

    accumulator = accumulator.to(tl.float32)

    b_mask = offs_n < N
    bias = tl.load(B_ptr, mask=b_mask, other=0.0).to(tl.float32)
    accumulator += bias[None, :]

    GELU_COEF_1 = 0.044715
    GELU_COEF_2 = 0.7978845608028654
    GELU_COEF_3 = 0.5
    x = accumulator
    x_cubed = x * x * x
    inner = GELU_COEF_1 * x_cubed + x
    inner_scaled = inner * GELU_COEF_2
    tanh_inner = tl.math.tanh(inner_scaled)
    gelu = GELU_COEF_3 * x * (1 + tanh_inner)

    output = gelu.to(tl.float16)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, output, mask=y_mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Shape mismatch: X{{K=}} != W{{K_check=}}"
    assert B.shape == (N,), f"Bias shape {{B.shape}} != (N={{N}},)"
    assert X.dtype == torch.float16, f"X dtype {{X.dtype}} != float16"
    assert W.dtype == torch.float16, f"W dtype {{W.dtype}} != float16"
    assert B.dtype == torch.float32, f"B dtype {{B.dtype}} != float32"
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    linear_gelu_kernel[grid](
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
"""
        return {"code": code}