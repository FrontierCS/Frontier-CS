import torch
import triton
import triton.language as tl
import os

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, L_ptr,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    M, K, N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Offsets for rows
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Load targets: (BLOCK_M,)
    targets = tl.load(T_ptr + offs_m, mask=mask_m, other=0)
    
    # Initialize accumulators
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    s_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    target_logits = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Base pointer for X: (BLOCK_M, K)
    x_ptrs_base = X_ptr + offs_m[:, None] * stride_xm
    
    # Iterate over N in chunks
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Accumulator for this block of logits: (BLOCK_M, BLOCK_N)
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        # Iterate over K in chunks to compute logits
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            
            # Load X tile: (BLOCK_M, BLOCK_K)
            x_ptrs = x_ptrs_base + offs_k[None, :] * stride_xk
            x_val = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
            
            # Load W tile: (BLOCK_K, BLOCK_N)
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            w_val = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
            
            # Accumulate dot product
            acc += tl.dot(x_val, w_val)
            
        # Add bias: (BLOCK_N,) -> broadcast to (BLOCK_M, BLOCK_N)
        b_val = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        acc += b_val[None, :]
        
        # Online Softmax updates
        # Mask out invalid columns for max computation
        acc_masked = tl.where(mask_n[None, :], acc, float("-inf"))
        
        # 1. Update max
        m_curr = tl.max(acc_masked, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        # 2. Update sum_exp
        # s_i = s_i * exp(m_i - m_new) + sum(exp(acc - m_new))
        term1 = s_i * tl.exp(m_i - m_new)
        term2 = tl.sum(tl.exp(acc_masked - m_new[:, None]), 1)
        s_i = term1 + term2
        
        m_i = m_new
        
        # 3. Extract target logit
        # Check if targets are in the current block of N
        # targets: (BLOCK_M,), offs_n: (BLOCK_N,)
        t_mask = (targets[:, None] == offs_n[None, :])
        # Use unmasked acc to avoid picking up -inf if target happened to be invalid (shouldn't happen for valid targets)
        # However, we need to ensure we only pick from valid N columns.
        t_mask = t_mask & mask_n[None, :]
        target_logits += tl.sum(tl.where(t_mask, acc, 0.0), 1)

    # Compute Final Loss
    # loss = log(s_i) + m_i - target_logits
    loss = tl.log(s_i) + m_i - target_logits
    
    # Store result
    tl.store(L_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    """
    M, K = X.shape
    K2, N = W.shape
    assert K == K2, "Dimension mismatch between X and W"
    assert B.shape[0] == N, "Dimension mismatch between W and B"
    assert targets.shape[0] == M, "Dimension mismatch between X and targets"
    
    # Output tensor
    loss = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Grid calculation
    grid = lambda META: ((M + META['BLOCK_M'] - 1) // META['BLOCK_M'],)
    
    fused_linear_ce_kernel[grid](
        X, W, B, targets, loss,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        M, K, N
    )
    
    return loss

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}