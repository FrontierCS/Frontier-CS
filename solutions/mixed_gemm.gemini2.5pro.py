import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def linear_gelu_kernel(
    X, W, B, Y,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    \"\"\"
    Triton kernel for mixed-precision Linear + Bias + GELU.
    \"\"\"
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of C it computes.
    # This is a 2D grid where each block computes a `BLOCK_SIZE_M x BLOCK_SIZE_N` tile.
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # ----------------------------------------------------------
    # Create pointers for the inputs and outputs.
    # We create a grid of pointers for the tiles of X and W that we will load.
    # `offs_m` and `offs_n` are ranges from 0 to `BLOCK_SIZE_M` and `BLOCK_SIZE_N`.
    # `offs_k` is a range from 0 to `BLOCK_SIZE_K`.
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    # -----------------------------------------------------------
    # Initialize the accumulator with zeros.
    # `accumulator` is a `BLOCK_SIZE_M x BLOCK_SIZE_N` tile of registers.
    # We use `tl.float32` for the accumulator for higher precision.
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # -----------------------------------------------------------
    # Main loop over the K dimension.
    for k in range(0, K, BLOCK_SIZE_K):
        # We need to handle the case where K is not a multiple of BLOCK_SIZE_K.
        # This is done by masking the loads.
        k_range = k + offs_k
        
        # Load the next block of X and W.
        # `a` and `b` are `BLOCK_SIZE_M x BLOCK_SIZE_K` and `BLOCK_SIZE_K x BLOCK_SIZE_N` tiles.
        a = tl.load(x_ptrs, mask=k_range[None, :] < K, other=0.0)
        b = tl.load(w_ptrs, mask=k_range[:, None] < K, other=0.0)
        
        # Perform the matrix multiplication.
        accumulator = tl.dot(a, b, accumulator)
        
        # Advance the pointers to the next K block.
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk

    # -----------------------------------------------------------
    # After the main loop, we add the bias and apply the GELU activation.
    
    # Load the bias vector.
    b_ptrs = B + offs_n
    n_mask = offs_n < N
    bias = tl.load(b_ptrs, mask=n_mask, other=0.0)
    
    # Add bias to the accumulator.
    # The bias is broadcasted across the M dimension.
    result = accumulator + bias[None, :]

    # Apply GELU activation.
    # Formula: gelu(x) = 0.5 * x * (1.0 + erf(x / sqrt(2)))
    inv_sqrt2 = 0.7071067811865476
    result = 0.5 * result * (1.0 + tl.math.erf(result * inv_sqrt2))

    # -----------------------------------------------------------
    # Write the result to the output tensor Y.
    y_ptrs = Y + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    m_mask = offs_m < M
    mask = m_mask[:, None] & n_mask[None, :]
    
    tl.store(y_ptrs, result.to(tl.float16), mask=mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Linear layer with GELU activation computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
    
    Returns:
        Output tensor of shape (M, N) - output with GELU activation (float16)
    \"\"\"
    M, K = X.shape
    K_W, N = W.shape

    assert K == K_W, "Inner dimensions of X and W must match"
    assert W.shape[1] == B.shape[0], "Dimensions of W and B must match"
    assert X.is_contiguous() and W.is_contiguous(), "Input tensors must be contiguous"

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
        triton.cdiv(N, META['BLOCK_SIZE_N']),
    )
    
    # Heuristically chosen parameters for good performance on L4.
    # Larger block sizes for M and N to increase computation per thread block.
    # A moderate K block size to balance register usage and parallelism.
    # num_warps and num_stages are tuned for latency hiding.
    BLOCK_SIZE_M = 128
    BLOCK_SIZE_N = 128
    BLOCK_SIZE_K = 64
    num_warps = 8
    num_stages = 3

    linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        num_warps=num_warps,
        num_stages=num_stages
    )
    
    return Y
"""
        return {"code": kernel_code}
