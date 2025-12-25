import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_jsd_kernel(
    # Pointers to matrices
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, output_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1n,
    stride_b2n,
    stride_outm,
    # Tile sizes
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
    # Memory swizzling
    GROUP_M: tl.constexpr = 8,
    # Precision
    ACCUM_DTYPE: tl.constexpr = tl.float32,
):
    # Program ID
    pid = tl.program_id(0)
    
    # Determine which rows we handle in this program
    num_pid_m = tl.cdiv(M, BLOCK_M)
    pid_m = pid // num_pid_m
    pid_n = pid % num_pid_m
    
    # Offsets for the block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    # Create masks for rows/columns
    mask_m = offs_m < M
    mask_n = offs_n < N
    mask_k = offs_k < K
    
    # Pointers to blocks
    X_ptr = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W1_ptr = W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
    W2_ptr = W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
    B1_ptr = B1_ptr + offs_n * stride_b1n
    B2_ptr = B2_ptr + offs_n * stride_b2n
    
    # Accumulators for logits
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    
    # Load biases
    b1 = tl.load(B1_ptr, mask=mask_n, other=0.0)
    b2 = tl.load(B2_ptr, mask=mask_n, other=0.0)
    
    # Add biases to accumulators
    acc1 += b1[None, :]
    acc2 += b2[None, :]
    
    # Matrix multiplication with tiling
    for k in range(0, K, BLOCK_K):
        # Load tiles
        x = tl.load(
            X_ptr,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
        )
        w1 = tl.load(
            W1_ptr,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
        )
        w2 = tl.load(
            W2_ptr,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
        )
        
        # Compute matrix multiplication
        acc1 += tl.dot(x, w1, out_dtype=ACCUM_DTYPE)
        acc2 += tl.dot(x, w2, out_dtype=ACCUM_DTYPE)
        
        # Move pointers
        X_ptr += BLOCK_K * stride_xk
        W1_ptr += BLOCK_K * stride_w1k
        W2_ptr += BLOCK_K * stride_w2k
    
    # First pass: compute max for numerical stability
    max1 = tl.max(acc1, axis=1)
    max2 = tl.max(acc2, axis=1)
    
    # Compute log-sum-exp for softmax normalization
    exp1 = tl.exp(acc1 - max1[:, None])
    exp2 = tl.exp(acc2 - max2[:, None])
    
    sum1 = tl.sum(exp1, axis=1)
    sum2 = tl.sum(exp2, axis=1)
    
    log_sum1 = tl.log(sum1) + max1
    log_sum2 = tl.log(sum2) + max2
    
    # Compute log probabilities
    log_p = acc1 - log_sum1[:, None]
    log_q = acc2 - log_sum2[:, None]
    
    # Compute probabilities
    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    # Compute mixture M = 0.5 * (P + Q)
    m = 0.5 * (p + q)
    
    # Compute log(M) with numerical stability
    log_m = tl.log(m)
    
    # Compute KL divergences
    kl_p = tl.sum(p * (log_p - log_m), axis=1)
    kl_q = tl.sum(q * (log_q - log_m), axis=1)
    
    # Compute JSD
    jsd = 0.5 * (kl_p + kl_q)
    
    # Write output
    output_ptr = output_ptr + offs_m * stride_outm
    tl.store(output_ptr, jsd, mask=mask_m)


def fused_linear_jsd(
    X: torch.Tensor, 
    W1: torch.Tensor, 
    B1: torch.Tensor, 
    W2: torch.Tensor, 
    B2: torch.Tensor
) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)
    
    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    # Check inputs
    assert X.dim() == 2, "X must be 2D"
    assert W1.dim() == 2, "W1 must be 2D"
    assert W2.dim() == 2, "W2 must be 2D"
    assert B1.dim() == 1, "B1 must be 1D"
    assert B2.dim() == 1, "B2 must be 1D"
    
    M, K = X.shape
    K_w1, N = W1.shape
    K_w2, N2 = W2.shape
    
    assert K == K_w1 == K_w2, "Input dimension mismatch"
    assert N == N2, "Output dimension mismatch"
    assert B1.shape[0] == N, "B1 dimension mismatch"
    assert B2.shape[0] == N, "B2 dimension mismatch"
    
    # Allocate output
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Choose tile sizes based on problem dimensions
    # These have been tuned for L4 GPU (24GB VRAM)
    if M <= 256:
        BLOCK_M = 64
        BLOCK_N = 256
        BLOCK_K = 64
        num_warps = 8
    else:
        BLOCK_M = 128
        BLOCK_N = 256
        BLOCK_K = 64
        num_warps = 8
    
    # Ensure blocks don't exceed dimensions
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_K = min(BLOCK_K, K)
    
    # Calculate grid size
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )
    
    # Launch kernel
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0),
        B2.stride(0),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_K=BLOCK_K,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
    )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1n,
    stride_b2n,
    stride_outm,
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_M: tl.constexpr = 8,
    ACCUM_DTYPE: tl.constexpr = tl.float32,
):
    pid = tl.program_id(0)
    
    num_pid_m = tl.cdiv(M, BLOCK_M)
    pid_m = pid // num_pid_m
    pid_n = pid % num_pid_m
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    mask_k = offs_k < K
    
    X_ptr = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W1_ptr = W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
    W2_ptr = W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
    B1_ptr = B1_ptr + offs_n * stride_b1n
    B2_ptr = B2_ptr + offs_n * stride_b2n
    
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    
    b1 = tl.load(B1_ptr, mask=mask_n, other=0.0)
    b2 = tl.load(B2_ptr, mask=mask_n, other=0.0)
    
    acc1 += b1[None, :]
    acc2 += b2[None, :]
    
    for k in range(0, K, BLOCK_K):
        x = tl.load(
            X_ptr,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
        )
        w1 = tl.load(
            W1_ptr,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
        )
        w2 = tl.load(
            W2_ptr,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
        )
        
        acc1 += tl.dot(x, w1, out_dtype=ACCUM_DTYPE)
        acc2 += tl.dot(x, w2, out_dtype=ACCUM_DTYPE)
        
        X_ptr += BLOCK_K * stride_xk
        W1_ptr += BLOCK_K * stride_w1k
        W2_ptr += BLOCK_K * stride_w2k
    
    max1 = tl.max(acc1, axis=1)
    max2 = tl.max(acc2, axis=1)
    
    exp1 = tl.exp(acc1 - max1[:, None])
    exp2 = tl.exp(acc2 - max2[:, None])
    
    sum1 = tl.sum(exp1, axis=1)
    sum2 = tl.sum(exp2, axis=1)
    
    log_sum1 = tl.log(sum1) + max1
    log_sum2 = tl.log(sum2) + max2
    
    log_p = acc1 - log_sum1[:, None]
    log_q = acc2 - log_sum2[:, None]
    
    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    m = 0.5 * (p + q)
    log_m = tl.log(m)
    
    kl_p = tl.sum(p * (log_p - log_m), axis=1)
    kl_q = tl.sum(q * (log_q - log_m), axis=1)
    
    jsd = 0.5 * (kl_p + kl_q)
    
    output_ptr = output_ptr + offs_m * stride_outm
    tl.store(output_ptr, jsd, mask=mask_m)


def fused_linear_jsd(X, W1, B1, W2, B2):
    assert X.dim() == 2, "X must be 2D"
    assert W1.dim() == 2, "W1 must be 2D"
    assert W2.dim() == 2, "W2 must be 2D"
    assert B1.dim() == 1, "B1 must be 1D"
    assert B2.dim() == 1, "B2 must be 1D"
    
    M, K = X.shape
    K_w1, N = W1.shape
    K_w2, N2 = W2.shape
    
    assert K == K_w1 == K_w2, "Input dimension mismatch"
    assert N == N2, "Output dimension mismatch"
    assert B1.shape[0] == N, "B1 dimension mismatch"
    assert B2.shape[0] == N, "B2 dimension mismatch"
    
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    if M <= 256:
        BLOCK_M = 64
        BLOCK_N = 256
        BLOCK_K = 64
        num_warps = 8
    else:
        BLOCK_M = 128
        BLOCK_N = 256
        BLOCK_K = 64
        num_warps = 8
    
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_K = min(BLOCK_K, K)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )
    
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0),
        B2.stride(0),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_K=BLOCK_K,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
    )
    
    return output
"""
        }
