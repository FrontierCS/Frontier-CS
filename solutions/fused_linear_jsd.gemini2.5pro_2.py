import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        fused_linear_jsd_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configs with 4 warps
        triton.Config({'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 1024, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        # More stages and warps
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _jsd_fwd_kernel_lse(
    X, W1, B1, W2, B2, LSE,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_lse_m, stride_lse_n,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    x_row_ptr = X + pid_m * stride_xm
    n_arange = tl.arange(0, BLOCK_N)
    k_arange = tl.arange(0, BLOCK_K)

    # --- Pass 1: compute max ---
    max1 = -float('inf')
    max2 = -float('inf')
    for n_block_start in range(0, tl.cdiv(N, BLOCK_N)):
        n_offsets = n_block_start * BLOCK_N + n_arange
        n_mask = n_offsets < N
        
        acc1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        
        for k_block_start in range(0, tl.cdiv(K, BLOCK_K)):
            k_offsets = k_block_start * BLOCK_K + k_arange
            k_mask = k_offsets < K
            
            x_tile = tl.load(x_row_ptr + k_offsets * stride_xk, mask=k_mask, other=0.0)
            
            w1_ptr = W1 + k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n
            w1_tile = tl.load(w1_ptr, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            w2_ptr = W2 + k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n
            w2_tile = tl.load(w2_ptr, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)

        b1_tile = tl.load(B1 + n_offsets, mask=n_mask, other=0.0)
        b2_tile = tl.load(B2 + n_offsets, mask=n_mask, other=0.0)
        
        logits1 = acc1 + b1_tile
        logits2 = acc2 + b2_tile
        
        max1 = tl.maximum(max1, tl.max(tl.where(n_mask, logits1, -float('inf')), axis=0))
        max2 = tl.maximum(max2, tl.max(tl.where(n_mask, logits2, -float('inf')), axis=0))

    # --- Pass 2: compute sum_exp ---
    sum_exp1 = 0.0
    sum_exp2 = 0.0
    for n_block_start in range(0, tl.cdiv(N, BLOCK_N)):
        n_offsets = n_block_start * BLOCK_N + n_arange
        n_mask = n_offsets < N

        acc1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        
        for k_block_start in range(0, tl.cdiv(K, BLOCK_K)):
            k_offsets = k_block_start * BLOCK_K + k_arange
            k_mask = k_offsets < K
            
            x_tile = tl.load(x_row_ptr + k_offsets * stride_xk, mask=k_mask, other=0.0)
            
            w1_ptr = W1 + k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n
            w1_tile = tl.load(w1_ptr, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            w2_ptr = W2 + k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n
            w2_tile = tl.load(w2_ptr, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)

        b1_tile = tl.load(B1 + n_offsets, mask=n_mask, other=0.0)
        b2_tile = tl.load(B2 + n_offsets, mask=n_mask, other=0.0)
        
        logits1 = acc1 + b1_tile
        logits2 = acc2 + b2_tile
        
        sum_exp1 += tl.sum(tl.where(n_mask, tl.exp(logits1 - max1), 0.0))
        sum_exp2 += tl.sum(tl.where(n_mask, tl.exp(logits2 - max2), 0.0))
        
    lse1 = max1 + tl.log(sum_exp1)
    lse2 = max2 + tl.log(sum_exp2)
    
    lse_row_ptr = LSE + pid_m * stride_lse_m
    tl.store(lse_row_ptr + 0 * stride_lse_n, lse1)
    tl.store(lse_row_ptr + 1 * stride_lse_n, lse2)

@triton.autotune(
    configs=[
        # Basic configs with 4 warps
        triton.Config({'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 1024, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        # More stages and warps
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _jsd_fwd_kernel_main(
    X, W1, B1, W2, B2, LSE, Out,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_lse_m, stride_lse_n,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)

    lse_row_ptr = LSE + pid_m * stride_lse_m
    lse1 = tl.load(lse_row_ptr + 0 * stride_lse_n)
    lse2 = tl.load(lse_row_ptr + 1 * stride_lse_n)
    
    x_row_ptr = X + pid_m * stride_xm
    jsd_sum = 0.0
    
    n_arange = tl.arange(0, BLOCK_N)
    k_arange = tl.arange(0, BLOCK_K)

    for n_block_start in range(0, tl.cdiv(N, BLOCK_N)):
        n_offsets = n_block_start * BLOCK_N + n_arange
        n_mask = n_offsets < N
        
        acc1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        
        for k_block_start in range(0, tl.cdiv(K, BLOCK_K)):
            k_offsets = k_block_start * BLOCK_K + k_arange
            k_mask = k_offsets < K
            
            x_tile = tl.load(x_row_ptr + k_offsets * stride_xk, mask=k_mask, other=0.0)
            
            w1_ptr = W1 + k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n
            w1_tile = tl.load(w1_ptr, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            w2_ptr = W2 + k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n
            w2_tile = tl.load(w2_ptr, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)
            
        b1_tile = tl.load(B1 + n_offsets, mask=n_mask, other=0.0)
        b2_tile = tl.load(B2 + n_offsets, mask=n_mask, other=0.0)
        
        logits1 = acc1 + b1_tile
        logits2 = acc2 + b2_tile
        
        logP = logits1 - lse1
        logQ = logits2 - lse2
        
        P = tl.exp(logP)
        Q = tl.exp(logQ)
        
        M = 0.5 * (P + Q)
        logM = tl.log(M)
        
        kl_p_terms = P * (logP - logM)
        kl_q_terms = Q * (logQ - logM)
        
        kl_p_terms = tl.where(P == 0.0, 0.0, kl_p_terms)
        kl_q_terms = tl.where(Q == 0.0, 0.0, kl_q_terms)
        kl_p_terms = tl.where(M == 0.0, 0.0, kl_p_terms)
        kl_q_terms = tl.where(M == 0.0, 0.0, kl_q_terms)

        jsd_terms = 0.5 * (kl_p_terms + kl_q_terms)
        jsd_sum += tl.sum(tl.where(n_mask, jsd_terms, 0.0))
        
    tl.store(Out + pid_m, jsd_sum)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _ , N = W1.shape
    
    LSE = torch.empty(M, 2, device=X.device, dtype=torch.float32)
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    grid = (M,)
    
    _jsd_fwd_kernel_lse[grid](
        X, W1, B1, W2, B2, LSE,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        LSE.stride(0), LSE.stride(1),
    )

    _jsd_fwd_kernel_main[grid](
        X, W1, B1, W2, B2, LSE, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        LSE.stride(0), LSE.stride(1),
    )
    
    return output
"""
        return {"code": fused_linear_jsd_code}
