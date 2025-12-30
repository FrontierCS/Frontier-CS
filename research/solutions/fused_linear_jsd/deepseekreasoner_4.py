import torch
import triton
import triton.language as tl
import math
from typing import Optional

@triton.jit
def _fused_linear_jsd_kernel(
    # Pointers to matrices
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    output_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    TWO_PASS: tl.constexpr,
    # Group size for reductions
    GROUP_SIZE_M: tl.constexpr = 8,
):
    # Program ID
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    # 2D grid: (pid_m, pid_n)
    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n
    
    # Offsets for the block
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Create masks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Initialize accumulators
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load bias (broadcast across M dimension)
    b1_ptrs = B1_ptr + offs_n
    b2_ptrs = B2_ptr + offs_n
    b1 = tl.load(b1_ptrs, mask=mask_n, other=0.0)
    b2 = tl.load(b2_ptrs, mask=mask_n, other=0.0)
    
    # Add bias to accumulators (broadcast bias across M dimension)
    acc1 += b1[None, :]
    acc2 += b2[None, :]
    
    # Compute dot product with tiling over K dimension
    for k in range(0, K, BLOCK_SIZE_K):
        # Create mask for K dimension
        mask_k = (k + offs_k) < K
        
        # Load X block
        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + 
                         (k + offs_k[None, :]) * stride_xk)
        x = tl.load(x_ptrs, 
                   mask=mask_m[:, None] & mask_k[None, :], 
                   other=0.0)
        
        # Load W1 block
        w1_ptrs = W1_ptr + ((k + offs_k[:, None]) * stride_w1k + 
                           offs_n[None, :] * stride_w1n)
        w1 = tl.load(w1_ptrs, 
                    mask=mask_k[:, None] & mask_n[None, :], 
                    other=0.0)
        
        # Load W2 block
        w2_ptrs = W2_ptr + ((k + offs_k[:, None]) * stride_w2k + 
                           offs_n[None, :] * stride_w2n)
        w2 = tl.load(w2_ptrs, 
                    mask=mask_k[:, None] & mask_n[None, :], 
                    other=0.0)
        
        # Convert to float32 for accumulation
        x_f32 = x.to(tl.float32)
        w1_f32 = w1.to(tl.float32)
        w2_f32 = w2.to(tl.float32)
        
        # Matrix multiply and accumulate
        acc1 += tl.dot(x_f32, w1_f32, allow_tf32=False)
        acc2 += tl.dot(x_f32, w2_f32, allow_tf32=False)
    
    # Two-pass algorithm for numerical stability
    if TWO_PASS:
        # First pass: compute log-sum-exp for each row
        # Find max for each row for numerical stability
        max1 = tl.max(acc1, axis=1)
        max2 = tl.max(acc2, axis=1)
        
        # Compute exp of shifted values
        exp_shifted1 = tl.exp(acc1 - max1[:, None])
        exp_shifted2 = tl.exp(acc2 - max2[:, None])
        
        # Sum along rows
        sum_exp1 = tl.sum(exp_shifted1, axis=1)
        sum_exp2 = tl.sum(exp_shifted2, axis=1)
        
        # Compute log probabilities (log softmax)
        log_prob1 = acc1 - max1[:, None] - tl.log(sum_exp1)[:, None]
        log_prob2 = acc2 - max2[:, None] - tl.log(sum_exp2)[:, None]
        
        # Compute probabilities
        prob1 = tl.exp(log_prob1)
        prob2 = tl.exp(log_prob2)
        
        # Compute mixture distribution M = 0.5*(P+Q)
        mixture = 0.5 * (prob1 + prob2)
        
        # Compute log mixture (with numerical stability)
        log_mixture = tl.log(mixture)
        
        # Compute KL divergences
        kl1 = prob1 * (log_prob1 - log_mixture)
        kl2 = prob2 * (log_prob2 - log_mixture)
        
        # Sum KL divergences to get JSD per sample
        jsd_per_sample = 0.5 * (tl.sum(kl1, axis=1) + tl.sum(kl2, axis=1))
        
        # Store final JSD values
        output_ptrs = output_ptr + offs_m
        tl.store(output_ptrs, jsd_per_sample, mask=mask_m)
    else:
        # Single-pass approximation (less stable but faster)
        # Compute softmax directly
        max1 = tl.max(acc1, axis=1)
        max2 = tl.max(acc2, axis=1)
        
        exp1 = tl.exp(acc1 - max1[:, None])
        exp2 = tl.exp(acc2 - max2[:, None])
        
        sum1 = tl.sum(exp1, axis=1)
        sum2 = tl.sum(exp2, axis=1)
        
        prob1 = exp1 / sum1[:, None]
        prob2 = exp2 / sum2[:, None]
        
        mixture = 0.5 * (prob1 + prob2)
        
        # Compute logs with epsilon for numerical stability
        eps = 1e-8
        log_prob1 = tl.log(prob1 + eps)
        log_prob2 = tl.log(prob2 + eps)
        log_mixture = tl.log(mixture + eps)
        
        kl1 = prob1 * (log_prob1 - log_mixture)
        kl2 = prob2 * (log_prob2 - log_mixture)
        
        jsd_per_sample = 0.5 * (tl.sum(kl1, axis=1) + tl.sum(kl2, axis=1))
        
        output_ptrs = output_ptr + offs_m
        tl.store(output_ptrs, jsd_per_sample, mask=mask_m)

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
    # Check input dimensions
    M, K = X.shape
    K_w1, N = W1.shape
    K_w2, N2 = W2.shape
    
    assert K == K_w1 == K_w2, f"Input dimension mismatch: X has K={K}, W1 has K={K_w1}, W2 has K={K_w2}"
    assert N == N2, f"Output dimension mismatch: W1 has N={N}, W2 has N={N2}"
    assert B1.shape == (N,), f"B1 shape mismatch: expected ({N},), got {B1.shape}"
    assert B2.shape == (N,), f"B2 shape mismatch: expected ({N},), got {B2.shape}"
    
    # Allocate output
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    # Choose optimal block sizes based on problem dimensions
    # These values are tuned for L4 GPU and typical sizes (M=128-256, K=2048, N=4096)
    if M <= 128:
        BLOCK_SIZE_M = 32
    elif M <= 256:
        BLOCK_SIZE_M = 64
    else:
        BLOCK_SIZE_M = 128
    
    BLOCK_SIZE_N = 128
    BLOCK_SIZE_K = 64
    
    # Compute grid size
    grid = (triton.cdiv(M, BLOCK_SIZE_M) * triton.cdiv(N, BLOCK_SIZE_N),)
    
    # Launch kernel
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        TWO_PASS=True,  # Use two-pass for better numerical stability
        GROUP_SIZE_M=8,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Return the complete implementation as code string
        import inspect
        code = inspect.getsource(__import__(__name__))
        return {"code": code}