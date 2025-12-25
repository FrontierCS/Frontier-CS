import torch
import triton
import triton.language as tl
import os

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    mask_m = offs_m < M
    
    # Load targets
    t_vals = tl.load(T_ptr + offs_m, mask=mask_m, other=0)
    
    # Initialize statistics for online softmax
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    d_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    target_logits = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        offs_n_curr = n_start + offs_n
        mask_n = offs_n_curr < N
        
        accum = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        for k_start in range(0, K, BLOCK_K):
            offs_k_curr = k_start + offs_k
            mask_k = offs_k_curr < K
            
            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k_curr[None, :] * stride_xk)
            x_tile = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0).to(tl.float16)
            
            w_ptrs = W_ptr + (offs_k_curr[:, None] * stride_wk + offs_n_curr[None, :] * stride_wn)
            w_tile = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float16)
            
            accum = tl.dot(x_tile, w_tile, accum)
            
        # Add bias
        b_ptrs = B_ptr + offs_n_curr
        b_tile = tl.load(b_ptrs, mask=mask_n, other=0.0).to(tl.float32)
        accum = accum + b_tile[None, :]
        
        # Mask out-of-bound N columns
        accum = tl.where(mask_n[None, :], accum, -float('inf'))
        
        # Online Softmax Update
        block_max = tl.max(accum, 1)
        new_m = tl.max(m_i, block_max)
        
        exp_logits = tl.exp(accum - new_m[:, None])
        block_sum = tl.sum(exp_logits, 1)
        
        d_i = d_i * tl.exp(m_i - new_m) + block_sum
        m_i = new_m
        
        # Accumulate target logit
        # Identify if target class is in this block
        cols = offs_n_curr[None, :]
        is_target = (cols == t_vals[:, None])
        # Masking accum with is_target selects the logit if target matches
        target_logits += tl.sum(accum * is_target, 1)
        
    # Final loss computation
    loss = tl.log(d_i) + m_i - target_logits
    
    tl.store(Loss_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    
    losses = torch.empty(M, device=X.device, dtype=torch.float32)
    
    grid = lambda META: ((M + META['BLOCK_M'] - 1) // META['BLOCK_M'],)
    
    fused_linear_ce_kernel[grid](
        X, W, B, targets, losses,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
    )
    
    return losses

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
