import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load targets
    # targets are long (int64)
    t = tl.load(T_ptr + offs_m, mask=mask_m, other=0)

    # Accumulators for online softmax
    # m_i: running max
    # d_i: running sum of exponentials
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    d_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    target_logits = tl.zeros([BLOCK_M], dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Load bias
        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        
        # Initialize accumulator with bias
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32) + b[None, :]
        
        # MatMul loop over K
        for start_k in range(0, K, BLOCK_K):
            offs_k = start_k + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            
            # Load X tile
            x_ptr = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            x = tl.load(x_ptr, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
            
            # Load W tile
            w_ptr = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            w = tl.load(w_ptr, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
            
            # Accumulate dot product
            acc += tl.dot(x, w)
            
        # -- Online Softmax Update --
        
        # 1. Update target logit if target is in this block
        # Check if t matches any column in this block
        col_mask = (t[:, None] == offs_n[None, :])
        # Ensure we don't access out of bounds N (though t < N implies safety)
        col_mask = col_mask & mask_n[None, :]
        
        # Extract the logits where col_mask is True
        target_val = tl.sum(acc * col_mask.to(tl.float32), 1)
        target_logits += target_val

        # 2. Update Max and Sum
        # Mask invalid columns for max/sum calculation
        acc_masked = tl.where(mask_n[None, :], acc, float('-inf'))
        
        block_max = tl.max(acc_masked, 1)
        new_max = tl.maximum(m_i, block_max)
        
        # Scale previous sum
        scale = tl.exp(m_i - new_max)
        d_i = d_i * scale
        
        # Add current block sum
        block_exp = tl.exp(acc_masked - new_max[:, None])
        d_i += tl.sum(block_exp, 1)
        
        m_i = new_max

    # Compute Final Loss
    # NLL = log(sum_exp) - target_logit + (shifted max correction)
    # log(sum(exp(x_i - m))) + m - x_target
    loss = tl.log(d_i) + m_i - target_logits
    tl.store(Out_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X, W, B, targets):
    M, K = X.shape
    K2, N = W.shape
    
    # Output tensor
    out = torch.empty((M,), dtype=torch.float32, device=X.device)
    
    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    
    # Grid configuration
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    fused_linear_ce_kernel[grid](
        X, W, B, targets, out,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn
    )
    
    return out
"""
        return {"code": code}
