import torch
import triton
import triton.language as tl
import os

@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_t, stride_o,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load targets for the current block of rows
    target_vals = tl.load(T_ptr + offs_m * stride_t, mask=mask_m, other=0)

    # Initialize running statistics for Online Softmax
    m_running = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    s_running = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    target_logits = tl.zeros([BLOCK_M], dtype=tl.float32)

    # Iterate over N (vocabulary) in blocks
    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Accumulate matrix multiplication result (logits)
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        # Iterate over K (features) in blocks
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            
            # Load X tile: (BLOCK_M, BLOCK_K)
            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            x_tile = tl.load(x_ptrs, mask=(mask_m[:, None] & mask_k[None, :]), other=0.0)
            
            # Load W tile: (BLOCK_K, BLOCK_N)
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            w_tile = tl.load(w_ptrs, mask=(mask_k[:, None] & mask_n[None, :]), other=0.0)
            
            acc += tl.dot(x_tile, w_tile)
        
        # Add bias
        b_ptrs = B_ptr + offs_n
        b_tile = tl.load(b_ptrs, mask=mask_n, other=0.0)
        logits = acc + b_tile[None, :]
        
        # Mask out-of-bounds columns to -inf
        logits = tl.where(mask_n[None, :], logits, float("-inf"))
        
        # Online Softmax Updates
        m_block = tl.max(logits, 1)
        m_new = tl.maximum(m_running, m_block)
        
        # Rescale running sum
        s_scale = tl.exp(m_running - m_new)
        s_running = s_running * s_scale
        
        # Add current block contribution
        p_block = tl.exp(logits - m_new[:, None])
        s_running = s_running + tl.sum(p_block, 1)
        
        # Update running max
        m_running = m_new
        
        # Extract target logits if they exist in this block
        t_broadcast = target_vals[:, None]
        n_broadcast = offs_n[None, :]
        mask_t = (t_broadcast == n_broadcast)
        
        target_logits += tl.sum(tl.where(mask_t, logits, 0.0), 1)

    # Compute Final Loss: -log(softmax(target)) = -target_logit + log(sum_exp)
    # log(sum_exp) = log(s_running * exp(m_running)) = log(s_running) + m_running
    loss = tl.log(s_running) + m_running - target_logits
    
    # Store output
    out_ptrs = Out_ptr + offs_m * stride_o
    tl.store(out_ptrs, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    out = torch.empty((M,), dtype=torch.float32, device=X.device)
    
    BLOCK_M = 16
    BLOCK_N = 128
    BLOCK_K = 64
    num_warps = 4
    
    grid = (triton.cdiv(M, BLOCK_M),)
    
    fused_linear_ce_kernel[grid](
        X, W, B, targets, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        targets.stride(0), out.stride(0),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=num_warps
    )
    return out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
