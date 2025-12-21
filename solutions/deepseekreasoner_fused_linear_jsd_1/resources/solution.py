import torch
import triton
import triton.language as tl
import math

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    assert X.is_cuda
    assert W1.shape == (K, N)
    assert W2.shape == (K, N)
    assert B1.shape == (N,)
    assert B2.shape == (N,)
    
    # Allocate output
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Choose grid size based on batch size
    # For small batch sizes, use more blocks for better parallelism
    # For large batch sizes, use fewer but larger blocks
    if M <= 256:
        BLOCK_M = 128
        BLOCK_N = 256
    else:
        BLOCK_M = 256
        BLOCK_N = 512
    
    # Launch kernel
    grid = (triton.cdiv(M, BLOCK_M),)
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_K=32,  # Fixed for better memory coalescing
        BLOCK_N=BLOCK_N,
        num_stages=4,
        num_warps=8,
    )
    
    return output

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    """
    Two-pass kernel for fused linear JSD computation.
    First pass: Compute log-sum-exp for both distributions
    Second pass: Compute JSD
    """
    pid_m = tl.program_id(0)
    
    # First pass: compute logits and log-sum-exp
    log_max1 = tl.full([BLOCK_N], float('-inf'), dtype=tl.float32)
    log_max2 = tl.full([BLOCK_N], float('-inf'), dtype=tl.float32)
    sum_exp1 = tl.full([BLOCK_N], 0.0, dtype=tl.float32)
    sum_exp2 = tl.full([BLOCK_N], 0.0, dtype=tl.float32)
    
    # Iterate over K dimension
    for k in range(0, K, BLOCK_K):
        # Load X
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_k = k + tl.arange(0, BLOCK_K)
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
                    mask=x_mask, other=0.0).to(tl.float32)
        
        # Iterate over N dimension in chunks
        for n in range(0, N, BLOCK_N):
            offs_n = n + tl.arange(0, BLOCK_N)
            n_mask = offs_n < N
            
            # Load weights
            w1 = tl.load(W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            w2 = tl.load(W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            
            # Compute partial matrix multiplication
            logits1_part = tl.dot(x, w1)
            logits2_part = tl.dot(x, w2)
            
            # Update max and sum-exp for log-sum-exp
            if k == 0:
                # Add bias on first iteration
                b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0)
                b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0)
                logits1_part += b1
                logits2_part += b2
                
                # Initialize max
                log_max1_local = tl.max(logits1_part, axis=1)
                log_max2_local = tl.max(logits2_part, axis=1)
            else:
                # Update max
                log_max1_local = tl.maximum(log_max1, tl.max(logits1_part, axis=1))
                log_max2_local = tl.maximum(log_max2, tl.max(logits2_part, axis=1))
            
            # Update sum-exp
            exp1 = tl.exp(logits1_part - log_max1[:, None])
            exp2 = tl.exp(logits2_part - log_max2[:, None])
            sum_exp1 += tl.sum(exp1, axis=1)
            sum_exp2 += tl.sum(exp2, axis=1)
            
            # Update max
            log_max1 = log_max1_local
            log_max2 = log_max2_local
    
    # Compute log-sum-exp
    log_sum_exp1 = log_max1 + tl.log(sum_exp1)
    log_sum_exp2 = log_max2 + tl.log(sum_exp2)
    
    # Second pass: compute JSD
    jsd = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Reset and recompute logits for JSD computation
    for k in range(0, K, BLOCK_K):
        # Load X
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_k = k + tl.arange(0, BLOCK_K)
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
                    mask=x_mask, other=0.0).to(tl.float32)
        
        # Iterate over N dimension in chunks
        for n in range(0, N, BLOCK_N):
            offs_n = n + tl.arange(0, BLOCK_N)
            n_mask = offs_n < N
            
            # Load weights
            w1 = tl.load(W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            w2 = tl.load(W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            
            # Compute logits
            logits1 = tl.dot(x, w1)
            logits2 = tl.dot(x, w2)
            
            if k == 0:
                # Add bias
                b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0)
                b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0)
                logits1 += b1
                logits2 += b2
            
            # Compute log probabilities
            log_p = logits1 - log_sum_exp1[:, None]
            log_q = logits2 - log_sum_exp2[:, None]
            
            # Compute probabilities
            p = tl.exp(log_p)
            q = tl.exp(log_q)
            
            # Compute M = 0.5*(P + Q) and log M
            m = 0.5 * (p + q)
            # Use log1p for numerical stability when m is small
            log_m = tl.where(m > 1e-8, tl.log(m), -18.0)
            
            # Compute KL divergences
            # Handle cases where p or q are 0 (log(0) would be -inf)
            kl_p = tl.where(p > 1e-8, p * (log_p - log_m), 0.0)
            kl_q = tl.where(q > 1e-8, q * (log_q - log_m), 0.0)
            
            # Accumulate JSD
            jsd += 0.5 * tl.sum(kl_p + kl_q, axis=1)
    
    # Store output
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask = offs_m < M
    tl.store(output_ptr + offs_m, jsd, mask=mask)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self):
        return """
import torch
import triton
import triton.language as tl
import math

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Fused linear layers with Jensen-Shannon Divergence computation.
    \"\"\"
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    assert X.is_cuda
    assert W1.shape == (K, N)
    assert W2.shape == (K, N)
    assert B1.shape == (N,)
    assert B2.shape == (N,)
    
    # Allocate output
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Choose grid size based on batch size
    if M <= 256:
        BLOCK_M = 128
        BLOCK_N = 256
    else:
        BLOCK_M = 256
        BLOCK_N = 512
    
    # Launch kernel
    grid = (triton.cdiv(M, BLOCK_M),)
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_K=32,
        BLOCK_N=BLOCK_N,
        num_stages=4,
        num_warps=8,
    )
    
    return output

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    \"\"\"
    Two-pass kernel for fused linear JSD computation.
    First pass: Compute log-sum-exp for both distributions
    Second pass: Compute JSD
    \"\"\"
    pid_m = tl.program_id(0)
    
    # First pass: compute logits and log-sum-exp
    log_max1 = tl.full([BLOCK_N], float('-inf'), dtype=tl.float32)
    log_max2 = tl.full([BLOCK_N], float('-inf'), dtype=tl.float32)
    sum_exp1 = tl.full([BLOCK_N], 0.0, dtype=tl.float32)
    sum_exp2 = tl.full([BLOCK_N], 0.0, dtype=tl.float32)
    
    # Iterate over K dimension
    for k in range(0, K, BLOCK_K):
        # Load X
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_k = k + tl.arange(0, BLOCK_K)
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
                    mask=x_mask, other=0.0).to(tl.float32)
        
        # Iterate over N dimension in chunks
        for n in range(0, N, BLOCK_N):
            offs_n = n + tl.arange(0, BLOCK_N)
            n_mask = offs_n < N
            
            # Load weights
            w1 = tl.load(W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            w2 = tl.load(W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            
            # Compute partial matrix multiplication
            logits1_part = tl.dot(x, w1)
            logits2_part = tl.dot(x, w2)
            
            # Update max and sum-exp for log-sum-exp
            if k == 0:
                # Add bias on first iteration
                b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0)
                b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0)
                logits1_part += b1
                logits2_part += b2
                
                # Initialize max
                log_max1_local = tl.max(logits1_part, axis=1)
                log_max2_local = tl.max(logits2_part, axis=1)
            else:
                # Update max
                log_max1_local = tl.maximum(log_max1, tl.max(logits1_part, axis=1))
                log_max2_local = tl.maximum(log_max2, tl.max(logits2_part, axis=1))
            
            # Update sum-exp
            exp1 = tl.exp(logits1_part - log_max1[:, None])
            exp2 = tl.exp(logits2_part - log_max2[:, None])
            sum_exp1 += tl.sum(exp1, axis=1)
            sum_exp2 += tl.sum(exp2, axis=1)
            
            # Update max
            log_max1 = log_max1_local
            log_max2 = log_max2_local
    
    # Compute log-sum-exp
    log_sum_exp1 = log_max1 + tl.log(sum_exp1)
    log_sum_exp2 = log_max2 + tl.log(sum_exp2)
    
    # Second pass: compute JSD
    jsd = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Reset and recompute logits for JSD computation
    for k in range(0, K, BLOCK_K):
        # Load X
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_k = k + tl.arange(0, BLOCK_K)
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
                    mask=x_mask, other=0.0).to(tl.float32)
        
        # Iterate over N dimension in chunks
        for n in range(0, N, BLOCK_N):
            offs_n = n + tl.arange(0, BLOCK_N)
            n_mask = offs_n < N
            
            # Load weights
            w1 = tl.load(W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            w2 = tl.load(W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                        mask=(offs_k[:, None] < K) & n_mask[None, :], other=0.0).to(tl.float32)
            
            # Compute logits
            logits1 = tl.dot(x, w1)
            logits2 = tl.dot(x, w2)
            
            if k == 0:
                # Add bias
                b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0)
                b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0)
                logits1 += b1
                logits2 += b2
            
            # Compute log probabilities
            log_p = logits1 - log_sum_exp1[:, None]
            log_q = logits2 - log_sum_exp2[:, None]
            
            # Compute probabilities
            p = tl.exp(log_p)
            q = tl.exp(log_q)
            
            # Compute M = 0.5*(P + Q) and log M
            m = 0.5 * (p + q)
            log_m = tl.where(m > 1e-8, tl.log(m), -18.0)
            
            # Compute KL divergences
            kl_p = tl.where(p > 1e-8, p * (log_p - log_m), 0.0)
            kl_q = tl.where(q > 1e-8, q * (log_q - log_m), 0.0)
            
            # Accumulate JSD
            jsd += 0.5 * tl.sum(kl_p + kl_q, axis=1)
    
    # Store output
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask = offs_m < M
    tl.store(output_ptr + offs_m, jsd, mask=mask)
"""
