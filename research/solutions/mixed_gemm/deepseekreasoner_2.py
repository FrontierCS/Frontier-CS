import torch
import triton
import triton.language as tl
import os
from typing import Optional


@triton.jit
def _gelu_activation(x):
    """GELU activation using libdevice erf."""
    # GELU(x) = 0.5 * x * (1 + erf(x / sqrt(2)))
    coeff = 0.7071067811865476  # 1/sqrt(2)
    erf_arg = x * coeff
    erf_result = tl.extra.cuda.libdevice.erf(erf_arg)
    return 0.5 * x * (1.0 + erf_result)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    # Pointers to matrices
    X_ptr, W_ptr, B_ptr, O_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_om, stride_on,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    """Mixed precision linear + bias + GELU kernel."""
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Offset for X and output
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers to X block
    X_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    # Pointers to W block
    W_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    # Pointers to bias
    B_ptrs = B_ptr + offs_n * stride_bn

    # Initialize accumulator to zero (float32)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over K dimension
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Load X and W with masking
        k_remaining = K - k * BLOCK_K
        X_mask = (offs_m[:, None] < M) & (offs_k[None, :] < k_remaining)
        W_mask = (offs_k[:, None] < k_remaining) & (offs_n[None, :] < N)
        
        X_block = tl.load(X_ptrs, mask=X_mask, other=0.0)
        W_block = tl.load(W_ptrs, mask=W_mask, other=0.0)
        
        # Compute matrix multiplication with fp16 inputs and fp32 accumulation
        acc += tl.dot(X_block, W_block, out_dtype=tl.float32)
        
        # Move pointers to next K block
        X_ptrs += BLOCK_K * stride_xk
        W_ptrs += BLOCK_K * stride_wk

    # Add bias (broadcasted over M dimension)
    bias = tl.load(B_ptrs, mask=offs_n < N, other=0.0)
    acc += bias[None, :]

    # Apply GELU activation
    output = _gelu_activation(acc)

    # Convert to fp16 for output
    output = output.to(tl.float16)

    # Write back output with masking
    offs_om = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_on = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    O_ptrs = O_ptr + offs_om[:, None] * stride_om + offs_on[None, :] * stride_on
    mask = (offs_om[:, None] < M) & (offs_on[None, :] < N)
    tl.store(O_ptrs, output, mask=mask)


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
    # Validate inputs
    assert X.dtype == torch.float16, f"X must be float16, got {X.dtype}"
    assert W.dtype == torch.float16, f"W must be float16, got {W.dtype}"
    assert B.dtype == torch.float32, f"B must be float32, got {B.dtype}"
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All tensors must be on CUDA"
    assert X.shape[1] == W.shape[0], f"X shape {X.shape}, W shape {W.shape}"
    assert W.shape[1] == B.shape[0], f"W shape {W.shape}, B shape {B.shape}"

    M, K = X.shape
    N = W.shape[1]
    
    # Allocate output tensor
    output = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # Launch kernel
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    _linear_gelu_kernel[grid](
        X, W, B, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        output.stride(0), output.stride(1)
    )
    
    return output


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        current_file = os.path.abspath(__file__)
        return {"program_path": current_file}