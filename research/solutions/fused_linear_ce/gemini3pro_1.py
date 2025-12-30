import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Loss_ptr,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    M, K, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    
    offs_m = start_m + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Load targets
    t_ptrs = T_ptr + offs_m
    targets = tl.load(t_ptrs, mask=mask_m, other=0)
    
    # Initialize stats
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    s_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    tgt_logit = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    offs_k = tl.arange(0, BLOCK_K)
    offs_n = tl.arange(0, BLOCK_N)
    
    # Base pointer for X
    x_base = X_ptr + offs_m[:, None] * stride_xm
    
    for start_n in range(0, N, BLOCK_N):
        # Accumulator for matrix multiplication
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        # Base pointer for W
        w_base = W_ptr + (start_n + offs_n)[None, :] * stride_wn
        
        # Inner loop over K
        for start_k in range(0, K, BLOCK_K):
            # Load X [BLOCK_M, BLOCK_K]
            x_ptrs = x_base + (start_k + offs_k)[None, :] * stride_xk
            x = tl.load(x_ptrs, mask=mask_m[:, None], other=0.0)
            
            # Load W [BLOCK_K, BLOCK_N]
            w_ptrs = w_base + (start_k + offs_k)[:, None] * stride_wk
            w = tl.load(w_ptrs)
            
            acc += tl.dot(x, w)
            
        # Add Bias
        b_ptrs = B_ptr + (start_n + offs_n)
        b = tl.load(b_ptrs)
        acc += b[None, :]
        
        # Online Softmax Update
        block_max = tl.max(acc, 1)
        m_new = tl.maximum(m_i, block_max)
        
        # Rescale sum
        s_i = s_i * tl.exp(m_i - m_new)
        m_i = m_new
        
        # Add current block exp
        s_i += tl.sum(tl.exp(acc - m_i[:, None]), 1)
        
        # Extract target logits
        cols = start_n + offs_n
        cols_i64 = cols.to(tl.int64)
        mask_t = (targets[:, None] == cols_i64[None, :])
        
        tgt_logit += tl.sum(tl.where(mask_t, acc, 0.0), 1)

    # Final Loss calculation
    # loss = log(s) + m - target_logit
    loss = tl.log(s_i) + m_i - tgt_logit
    
    l_ptrs = Loss_ptr + offs_m
    tl.store(l_ptrs, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    
    losses = torch.empty(M, device=X.device, dtype=torch.float32)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    fused_linear_ce_kernel[grid](
        X, W, B, targets, losses,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        M, K, N
    )
    
    return losses
"""
        }