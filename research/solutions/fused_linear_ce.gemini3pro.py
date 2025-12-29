import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    M, N, K,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    
    # Load targets
    # targets are int64
    t_ptrs = T_ptr + offs_m
    targets = tl.load(t_ptrs, mask=offs_m < M, other=-1)
    
    # Initialize Accumulators
    # m_i: running max logit
    # d_i: running sum of exp(logit - m_i)
    # target_logits: stored logit for the target class
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    d_i = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    target_logits = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    
    # Iterate over N (vocabulary) in blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Accumulator for this block of logits
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        # Iterate over K (hidden dim) in blocks to compute logits
        for start_k in range(0, K, BLOCK_K):
            offs_k = start_k + tl.arange(0, BLOCK_K)
            
            # Load X tile: (BLOCK_M, BLOCK_K)
            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            x = tl.load(x_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < K), other=0.0)
            
            # Load W tile: (BLOCK_K, BLOCK_N)
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            w = tl.load(w_ptrs, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)
            
            # Matmul: Accumulate partial sums
            acc = tl.dot(x, w, acc)
            
        # Add Bias
        b_ptrs = B_ptr + offs_n
        b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        acc += b[None, :]
        
        # Mask out-of-bounds columns (padding)
        acc = tl.where(offs_n[None, :] < N, acc, float("-inf"))
        
        # --- Online Softmax / Reduction ---
        
        # 1. Update max
        m_block = tl.max(acc, 1) # (BLOCK_M,)
        m_new = tl.maximum(m_i, m_block)
        
        # 2. Update sum exp
        # d_new = d_i * exp(m_i - m_new) + sum(exp(acc - m_new))
        term1 = d_i * tl.exp(m_i - m_new)
        term2 = tl.sum(tl.exp(acc - m_new[:, None]), 1)
        d_new = term1 + term2
        
        m_i = m_new
        d_i = d_new
        
        # --- Extract Target Logit ---
        # Check which columns in this block match the target indices
        # Cast offs_n to int64 for comparison with targets
        offs_n_64 = offs_n.to(tl.int64)
        is_target = targets[:, None] == offs_n_64[None, :]
        
        # Add the logit value if it is the target
        target_val = tl.sum(tl.where(is_target, acc, 0.0), 1)
        target_logits += target_val

    # Final Loss Calculation
    # NLL = -log(softmax(target)) = -target_logit + log(sum_exp)
    # log(sum_exp) = log(d_i * exp(m_i)) = log(d_i) + m_i
    # L = m_i + log(d_i) - target_logits
    
    loss = m_i + tl.log(d_i) - target_logits
    
    # Store result
    o_ptrs = Out_ptr + offs_m
    tl.store(o_ptrs, loss, mask=offs_m < M)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K2, N = W.shape
    assert K == K2, "Dimension mismatch between X and W"
    
    # Output tensor
    losses = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # 1D Grid over M
    grid = lambda META: ((M + META['BLOCK_M'] - 1) // META['BLOCK_M'],)
    
    fused_linear_ce_kernel[grid](
        X, W, B, targets, losses,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        M, N, K
    )
    
    return losses
"""}