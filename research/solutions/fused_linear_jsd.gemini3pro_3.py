import torch
import triton
import triton.language as tl

# We define the kernel code as a string to return in Solution.solve
# and also execute it to provide the required function in the current scope.
KERNEL_CODE = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 4}, num_stages=3),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_warps': 8}, num_stages=3),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32, 'num_warps': 8}, num_stages=3),
        triton.Config({'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 4}, num_stages=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Out_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    # Each program handles one row of M
    pid_m = tl.program_id(0)
    
    # Base pointer for X row
    x_base = X_ptr + pid_m * stride_xm
    
    # -----------------------------------------------------------
    # Pass 1: Compute LogSumExp (LSE) for row m
    # We use FlashAttention-style recomputation (online softmax) 
    # but since we need LSE before JSD, we do two passes over N/K blocks.
    # -----------------------------------------------------------
    
    # Stats for LogSumExp: max (m), sum_exp (d)
    m1 = -float('inf')
    d1 = 0.0
    m2 = -float('inf')
    d2 = 0.0
    
    # Iterate over N in blocks
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Load Bias: (BLOCK_N,)
        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        
        # Accumulators (1, BLOCK_N) - initialize with bias
        acc1 = b1[None, :]
        acc2 = b2[None, :]
        
        # Iterate over K to compute logits tile
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            
            # Load X tile: (1, BLOCK_K)
            x = tl.load(x_base + offs_k * stride_xk, mask=mask_k, other=0.0).to(tl.float16)
            x = x[None, :] # Ensure 2D for dot
            
            # Load W tiles: (BLOCK_K, BLOCK_N)
            w1_ptr_base = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
            w2_ptr_base = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
            
            w1 = tl.load(w1_ptr_base, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float16)
            w2 = tl.load(w2_ptr_base, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float16)
            
            # Accumulate dot product
            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)
        
        # Mask padded elements with -inf for Softmax stats
        acc1 = tl.where(mask_n[None, :], acc1, -float('inf'))
        acc2 = tl.where(mask_n[None, :], acc2, -float('inf'))
        
        # Update LSE stats 1
        max1_block = tl.max(acc1, axis=1)
        new_m1 = tl.maximum(m1, max1_block)
        # Handle exp stability: exp(m - new_m)
        d1 = d1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(acc1 - new_m1), axis=1)
        m1 = new_m1
        
        # Update LSE stats 2
        max2_block = tl.max(acc2, axis=1)
        new_m2 = tl.maximum(m2, max2_block)
        d2 = d2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(acc2 - new_m2), axis=1)
        m2 = new_m2

    # Final LSE
    lse1 = m1 + tl.log(d1)
    lse2 = m2 + tl.log(d2)
    
    # -----------------------------------------------------------
    # Pass 2: Compute JSD
    # Recompute logits and accumulate JSD terms
    # -----------------------------------------------------------
    jsd_sum = 0.0
    
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Reload/Recompute
        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        
        acc1 = b1[None, :]
        acc2 = b2[None, :]
        
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            
            x = tl.load(x_base + offs_k * stride_xk, mask=mask_k, other=0.0).to(tl.float16)
            x = x[None, :]
            
            w1_ptr_base = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
            w2_ptr_base = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
            
            w1 = tl.load(w1_ptr_base, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float16)
            w2 = tl.load(w2_ptr_base, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float16)
            
            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)
        
        # Mask padded elements to -inf for correct probabilities
        acc1 = tl.where(mask_n[None, :], acc1, -float('inf'))
        acc2 = tl.where(mask_n[None, :], acc2, -float('inf'))
        
        # Compute probabilities
        p = tl.exp(acc1 - lse1)
        q = tl.exp(acc2 - lse2)
        
        # Ensure 0 in padded region
        p = tl.where(mask_n[None, :], p, 0.0)
        q = tl.where(mask_n[None, :], q, 0.0)
        
        # Mean distribution
        m_prob = 0.5 * (p + q)
        
        # log(M) with epsilon for stability (though M=0 implies P=Q=0 so term=0)
        log_m = tl.log(m_prob + 1e-20)
        
        # KL terms: P * (logP - logM) = P * (logits - lse - logM)
        # If P=0, P*logP -> 0. P*anything finite -> 0.
        # But logits are -inf. P * logits = 0 * -inf = NaN.
        # So we must guard the calculation.
        
        term1 = p * (acc1 - lse1 - log_m)
        term2 = q * (acc2 - lse2 - log_m)
        
        # Mask out NaN/invalid terms from padding
        term1 = tl.where(mask_n[None, :], term1, 0.0)
        term2 = tl.where(mask_n[None, :], term2, 0.0)
        
        jsd_sum += tl.sum(term1 + term2)
        
    tl.store(Out_ptr + pid_m, 0.5 * jsd_sum)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    
    # Output tensor
    Out = torch.empty((M,), dtype=torch.float32, device=X.device)
    
    # 1 block per row
    grid = (M,)
    
    fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, Out,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
    )
    return Out
"""

# Execute the kernel code to define functions in the current scope
exec(KERNEL_CODE)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns the optimized Triton code.
        """
        return {"code": KERNEL_CODE}
