import torch
import triton
import triton.language as tl
from triton.language.extra.cuda import libdevice

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        # Configurations with larger K block
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=4),
        # Larger tiles
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
        # High performance configuration
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X, W, B, Y,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    """
    Triton kernel for Fused Linear + Bias + GELU.
    Computes Y = GELU(X @ W + B).
    """
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of Y it should compute.
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # ----------------------------------------------------------
    # Create pointers for the inputs and outputs.
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # -----------------------------------------------------------
    # Main computation
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        # Load the next block of X and W, masking for out-of-bounds accesses.
        k_remaining = K - k
        x_block = tl.load(x_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < k_remaining), other=0.0)
        w_block = tl.load(w_ptrs, mask=(offs_k[:, None] < k_remaining) & (offs_n[None, :] < N), other=0.0)
        
        # Perform matrix multiplication and accumulate.
        accumulator += tl.dot(x_block, w_block)
        
        # Advance pointers to the next K-block.
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk

    # -----------------------------------------------------------
    # Epilogue: Add bias and apply GELU
    
    # Load the bias vector.
    b_ptrs = B + offs_n
    b_block = tl.load(b_ptrs, mask=offs_n < N, other=0.0)

    # Add bias to the accumulator.
    accumulator += b_block[None, :]

    # Apply the GELU activation function.
    # GELU(x) = x * 0.5 * (1 + erf(x / sqrt(2)))
    INV_SQRT_2 = 0.7071067811865476
    erf_input = accumulator * INV_SQRT_2
    erf_val = libdevice.erf(erf_input.to(tl.float32)) # Use libdevice as suggested
    gelu_output = accumulator * 0.5 * (1.0 + erf_val)

    # Cast the final result to the output type (float16).
    output = gelu_output.to(tl.float16)

    # -----------------------------------------------------------
    # Write the final result to the output tensor Y.
    y_ptrs = Y + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    tl.store(y_ptrs, output, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


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
    # Check constraints for robustness.
    assert X.shape[1] == W.shape[0], "Incompatible dimensions for matrix multiplication"
    assert B.shape[0] == W.shape[1], "Incompatible dimensions for bias"
    assert X.is_cuda and W.is_cuda and B.is_cuda, "Input tensors must be on a CUDA device"
    assert X.dtype == torch.float16, "Input tensor X must be float16"
    assert W.dtype == torch.float16, "Weight tensor W must be float16"
    assert B.dtype == torch.float32, "Bias tensor B must be float32"

    M, K = X.shape
    _, N = W.shape

    # Allocate the output tensor.
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    # Define the grid for launching the kernel.
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
        triton.cdiv(N, META['BLOCK_SIZE_N']),
    )

    # Launch the kernel.
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # The entire python code as a single string
        code = '''
import torch
import triton
import triton.language as tl
from triton.language.extra.cuda import libdevice

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        # Configurations with larger K block
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=4),
        # Larger tiles
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
        # High performance configuration
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X, W, B, Y,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    """
    Triton kernel for Fused Linear + Bias + GELU.
    Computes Y = GELU(X @ W + B).
    """
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of Y it should compute.
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # ----------------------------------------------------------
    # Create pointers for the inputs and outputs.
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # -----------------------------------------------------------
    # Main computation
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        # Load the next block of X and W, masking for out-of-bounds accesses.
        k_remaining = K - k
        x_block = tl.load(x_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < k_remaining), other=0.0)
        w_block = tl.load(w_ptrs, mask=(offs_k[:, None] < k_remaining) & (offs_n[None, :] < N), other=0.0)
        
        # Perform matrix multiplication and accumulate.
        accumulator += tl.dot(x_block, w_block)
        
        # Advance pointers to the next K-block.
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk

    # -----------------------------------------------------------
    # Epilogue: Add bias and apply GELU
    
    # Load the bias vector.
    b_ptrs = B + offs_n
    b_block = tl.load(b_ptrs, mask=offs_n < N, other=0.0)

    # Add bias to the accumulator.
    accumulator += b_block[None, :]

    # Apply the GELU activation function.
    # GELU(x) = x * 0.5 * (1 + erf(x / sqrt(2)))
    INV_SQRT_2 = 0.7071067811865476
    erf_input = accumulator * INV_SQRT_2
    erf_val = libdevice.erf(erf_input.to(tl.float32)) # Use libdevice as suggested
    gelu_output = accumulator * 0.5 * (1.0 + erf_val)

    # Cast the final result to the output type (float16).
    output = gelu_output.to(tl.float16)

    # -----------------------------------------------------------
    # Write the final result to the output tensor Y.
    y_ptrs = Y + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    tl.store(y_ptrs, output, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


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
    # Check constraints for robustness.
    assert X.shape[1] == W.shape[0], "Incompatible dimensions for matrix multiplication"
    assert B.shape[0] == W.shape[1], "Incompatible dimensions for bias"
    assert X.is_cuda and W.is_cuda and B.is_cuda, "Input tensors must be on a CUDA device"
    assert X.dtype == torch.float16, "Input tensor X must be float16"
    assert W.dtype == torch.float16, "Weight tensor W must be float16"
    assert B.dtype == torch.float32, "Bias tensor B must be float32"

    M, K = X.shape
    _, N = W.shape

    # Allocate the output tensor.
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    # Define the grid for launching the kernel.
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
        triton.cdiv(N, META['BLOCK_SIZE_N']),
    )

    # Launch the kernel.
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
    )

    return Y
'''
        return {"code": code}
