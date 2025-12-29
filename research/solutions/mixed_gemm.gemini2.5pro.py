import os
import torch
import triton
import triton.language as tl

@triton.jit
def _linear_gelu_kernel(
    # Pointers to matrices
    X_ptr, W_ptr, B_ptr, Y_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_ym, stride_yn,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr
):
    """
    Triton kernel for fused Linear + Bias + GELU.
    """
    # -----------------------------------------------------------
    # Map program ids to M and N dimensions to form a 2D grid of blocks
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # ----------------------------------------------------------
    # Create offsets for the current block
    # These are the ranges of indices that this block will compute
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    # ----------------------------------------------------------
    # Initialize pointers to the first K-block of X and W
    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # -----------------------------------------------------------
    # Initialize accumulator with zeros, using float32 for precision
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # -----------------------------------------------------------
    # Loop over the K dimension in blocks of BLOCK_SIZE_K
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Correctly mask the K dimension for the last (potentially partial) block
        k_indices = k * BLOCK_SIZE_K + offs_k
        
        # Create masks for loading X and W tiles safely
        x_mask = (offs_m[:, None] < M) & (k_indices[None, :] < K)
        w_mask = (k_indices[:, None] < K) & (offs_n[None, :] < N)
        
        # Load the tiles of X and W from global memory
        # Use the masks to prevent out-of-bounds memory access
        x_tile = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w_tile = tl.load(w_ptrs, mask=w_mask, other=0.0)
        
        # Perform the matrix multiplication and accumulate the result in float32
        accumulator = tl.dot(x_tile, w_tile, accumulator)
        
        # Advance the pointers to the next K-block
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk

    # -----------------------------------------------------------
    # Load and add bias vector B
    # Bias is of shape (N,), so we only need offsets in the N dimension
    b_ptrs = B_ptr + offs_n * stride_bn
    b_mask = offs_n < N
    bias = tl.load(b_ptrs, mask=b_mask, other=0.0)
    
    # Add bias to the accumulator. The bias is broadcast across the M dimension.
    accumulator += bias[None, :]

    # -----------------------------------------------------------
    # Apply GELU activation function
    # GELU(x) = x * 0.5 * (1.0 + erf(x / sqrt(2)))
    GELU_SCALAR = 0.7071067811865476  # 1/sqrt(2)
    erf_input = accumulator * GELU_SCALAR
    erf_output = tl.extra.cuda.libdevice.erf(erf_input)
    gelu_output = accumulator * 0.5 * (1.0 + erf_output)

    # -----------------------------------------------------------
    # Write the final result to the output matrix Y
    # Convert the result to float16 before storing
    output_f16 = gelu_output.to(Y_ptr.dtype.element_ty)

    # Create pointers and masks for storing the output block
    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, output_f16, mask=y_mask)


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
    # Input validation
    assert X.is_cuda and W.is_cuda and B.is_cuda, "All tensors must be on a CUDA device."
    assert X.dtype == torch.float16, "Input X must be float16."
    assert W.dtype == torch.float16, "Weight W must be float16."
    assert B.dtype == torch.float32, "Bias B must be float32."
    assert X.shape[1] == W.shape[0], "Incompatible dimensions for matrix multiplication."
    assert B.shape[0] == W.shape[1], "Bias dimension mismatch."
    
    M, K = X.shape
    _, N = W.shape
    
    # Allocate the output tensor
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    # Kernel launch grid
    grid = (triton.cdiv(M, 128), triton.cdiv(N, 128))
    
    # Heuristically chosen tuning parameters for good performance on modern GPUs
    # These parameters control the tiling of the computation.
    BLOCK_SIZE_M = 128
    BLOCK_SIZE_N = 128
    BLOCK_SIZE_K = 32
    num_warps = 8
    num_stages = 3

    # Launch the Triton kernel
    _linear_gelu_kernel[grid](
        # Tensors
        X, W, B, Y,
        # Dimensions
        M, N, K,
        # Strides
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
        # Meta-parameters (compile-time constants)
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        num_warps=num_warps,
        num_stages=num_stages
    )
    
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # We return the path to the current file, which contains the
        # kernel and launcher implementation.
        return {"program_path": os.path.abspath(__file__)}