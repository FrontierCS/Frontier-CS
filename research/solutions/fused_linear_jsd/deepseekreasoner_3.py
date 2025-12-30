import torch
import triton
import triton.language as tl
import os

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                     W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    # Check inputs
    M, K = X.shape
    N = W1.shape[1]
    assert W1.shape == (K, N), f"W1 shape mismatch: {W1.shape} != ({K}, {N})"
    assert W2.shape == (K, N), f"W2 shape mismatch: {W2.shape} != ({K}, {N})"
    assert B1.shape == (N,), f"B1 shape mismatch: {B1.shape} != ({N},)"
    assert B2.shape == (N,), f"B2 shape mismatch: {B2.shape} != ({N},)"
    
    # Allocate output tensor
    out = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Launch kernel with optimized grid configuration
    BLOCK_M = 64
    BLOCK_N = 128
    grid = (triton.cdiv(M, BLOCK_M),)
    
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0),
        B2.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=32,
        num_warps=4,
        num_stages=3
    )
    
    return out

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, out_ptr,
    M, N, K,
    stride_Xm, stride_Xk,
    stride_W1k, stride_W1n,
    stride_W2k, stride_W2n,
    stride_B1n,
    stride_B2n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    """
    Triton kernel for fused linear JSD computation.
    """
    pid_m = tl.program_id(0)
    
    # Range of rows this program handles
    m_start = pid_m * BLOCK_M
    m_offsets = m_start + tl.arange(0, BLOCK_M)
    m_mask = m_offsets < M
    
    # Initialize output
    out_acc = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # First pass: compute log-sum-exp for both branches
    logsumexp1 = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    logsumexp2 = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    sumexp1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    sumexp2 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process N dimension in tiles
    for n_start in range(0, N, BLOCK_N):
        n_offsets = n_start + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N
        
        # Initialize accumulators for this tile
        logits1_acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        logits2_acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        
        # Process K dimension in tiles
        for k_start in range(0, K, BLOCK_K):
            k_offsets = k_start + tl.arange(0, BLOCK_K)
            k_mask = k_offsets < K
            
            # Load input tile
            x_ptrs = X_ptr + m_offsets[:, None] * stride_Xm + k_offsets[None, :] * stride_Xk
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            
            # Load weight tiles
            w1_ptrs = W1_ptr + k_offsets[:, None] * stride_W1k + n_offsets[None, :] * stride_W1n
            w1 = tl.load(w1_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            w2_ptrs = W2_ptr + k_offsets[:, None] * stride_W2k + n_offsets[None, :] * stride_W2n
            w2 = tl.load(w2_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            # Matrix multiplication with accumulation
            logits1_acc += tl.dot(x, w1, allow_tf32=True)
            logits2_acc += tl.dot(x, w2, allow_tf32=True)
        
        # Load bias tiles
        b1_ptrs = B1_ptr + n_offsets * stride_B1n
        b1 = tl.load(b1_ptrs, mask=n_mask, other=0.0).to(tl.float32)
        
        b2_ptrs = B2_ptr + n_offsets * stride_B2n
        b2 = tl.load(b2_ptrs, mask=n_mask, other=0.0).to(tl.float32)
        
        # Add biases
        logits1_acc += b1[None, :]
        logits2_acc += b2[None, :]
        
        # Update log-sum-exp for this tile
        tile_max1 = tl.max(logits1_acc, axis=1)
        tile_max2 = tl.max(logits2_acc, axis=1)
        
        # Compute exponential values safely
        exp1 = tl.exp(logits1_acc - tile_max1[:, None])
        exp2 = tl.exp(logits2_acc - tile_max2[:, None])
        
        # Update global max and sumexp
        # For branch 1
        old_max1 = tl.where(tile_max1 > logsumexp1, tile_max1, logsumexp1)
        new_max1 = tl.where(tile_max1 > logsumexp1, logsumexp1, tile_max1)
        
        sumexp1 = tl.where(tile_max1 > logsumexp1,
                          sumexp1 * tl.exp(new_max1 - old_max1) + tl.sum(exp1, axis=1),
                          sumexp1 + tl.sum(exp1, axis=1) * tl.exp(tile_max1 - old_max1))
        
        # For branch 2
        old_max2 = tl.where(tile_max2 > logsumexp2, tile_max2, logsumexp2)
        new_max2 = tl.where(tile_max2 > logsumexp2, logsumexp2, tile_max2)
        
        sumexp2 = tl.where(tile_max2 > logsumexp2,
                          sumexp2 * tl.exp(new_max2 - old_max2) + tl.sum(exp2, axis=1),
                          sumexp2 + tl.sum(exp2, axis=1) * tl.exp(tile_max2 - old_max2))
        
        logsumexp1 = old_max1
        logsumexp2 = old_max2
    
    # Compute final log-sum-exp
    lse1 = logsumexp1 + tl.log(sumexp1)
    lse2 = logsumexp2 + tl.log(sumexp2)
    
    # Second pass: compute JSD
    for n_start in range(0, N, BLOCK_N):
        n_offsets = n_start + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N
        
        # Initialize accumulators for this tile
        logits1_acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        logits2_acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        
        # Process K dimension in tiles
        for k_start in range(0, K, BLOCK_K):
            k_offsets = k_start + tl.arange(0, BLOCK_K)
            k_mask = k_offsets < K
            
            # Load input tile
            x_ptrs = X_ptr + m_offsets[:, None] * stride_Xm + k_offsets[None, :] * stride_Xk
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            
            # Load weight tiles
            w1_ptrs = W1_ptr + k_offsets[:, None] * stride_W1k + n_offsets[None, :] * stride_W1n
            w1 = tl.load(w1_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            w2_ptrs = W2_ptr + k_offsets[:, None] * stride_W2k + n_offsets[None, :] * stride_W2n
            w2 = tl.load(w2_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            # Matrix multiplication with accumulation
            logits1_acc += tl.dot(x, w1, allow_tf32=True)
            logits2_acc += tl.dot(x, w2, allow_tf32=True)
        
        # Load bias tiles
        b1_ptrs = B1_ptr + n_offsets * stride_B1n
        b1 = tl.load(b1_ptrs, mask=n_mask, other=0.0).to(tl.float32)
        
        b2_ptrs = B2_ptr + n_offsets * stride_B2n
        b2 = tl.load(b2_ptrs, mask=n_mask, other=0.0).to(tl.float32)
        
        # Add biases
        logits1_acc += b1[None, :]
        logits2_acc += b2[None, :]
        
        # Compute probabilities in log space
        log_p = logits1_acc - lse1[:, None]
        log_q = logits2_acc - lse2[:, None]
        
        # Compute probabilities
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        
        # Compute M = 0.5 * (P + Q)
        m = 0.5 * (p + q)
        
        # Compute log M safely (avoid log(0))
        log_m = tl.log(tl.where(m > 0, m, 1e-12))
        
        # Compute KL divergences
        # KL(P||M) = sum(P * (log P - log M))
        kl_pm = p * (log_p - log_m)
        kl_qm = q * (log_q - log_m)
        
        # Accumulate JSD contributions
        out_acc += tl.sum(0.5 * (kl_pm + kl_qm), axis=1)
    
    # Store output
    out_ptrs = out_ptr + m_offsets
    tl.store(out_ptrs, out_acc, mask=m_mask)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Read the current file and return its contents
        current_file = os.path.abspath(__file__)
        
        # For the purpose of this implementation, we'll return the code
        with open(current_file, 'r') as f:
            code_content = f.read()
        
        return {"code": code_content}