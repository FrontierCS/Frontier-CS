import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 128, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 2048, 'BLOCK_SIZE_K': 16, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 4096, 'BLOCK_SIZE_K': 16, 'num_stages': 4, 'num_warps': 16}, pre_hook=lambda args: args['N'] == 4096),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Out_ptr,
    M, N, K,
    stride_x_m, stride_x_k,
    stride_w1_k, stride_w1_n,
    stride_w2_k, stride_w2_n,
    stride_out_m,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    x_row_ptr = X_ptr + pid_m * stride_x_m

    # --- PASS 1: Compute log-sum-exp ---
    max1 = -float('inf')
    max2 = -float('inf')
    sum_exp1 = 0.0
    sum_exp2 = 0.0

    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n = n_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((1, BLOCK_SIZE_N), dtype=tl.float32)
        acc2 = tl.zeros((1, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            offs_k = k_start * BLOCK_SIZE_K + tl.arange(0, BLOCK_SIZE_K)
            
            x_ptr = x_row_ptr + offs_k * stride_x_k
            x = tl.load(x_ptr, mask=offs_k < K, other=0.0)
            x_mat = tl.reshape(x, (1, BLOCK_SIZE_K))

            w1_ptr = W1_ptr + (offs_k[:, None] * stride_w1_k + offs_n[None, :] * stride_w1_n)
            w1 = tl.load(w1_ptr, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)

            w2_ptr = W2_ptr + (offs_k[:, None] * stride_w2_k + offs_n[None, :] * stride_w2_n)
            w2 = tl.load(w2_ptr, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)

            acc1 += tl.dot(x_mat.to(w1.dtype), w1, out_dtype=tl.float32)
            acc2 += tl.dot(x_mat.to(w2.dtype), w2, out_dtype=tl.float32)

        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        
        logits1_block = tl.squeeze(acc1, axis=0) + b1
        logits2_block = tl.squeeze(acc2, axis=0) + b2

        block_max1 = tl.max(tl.where(mask_n, logits1_block, -float('inf')), axis=0)
        new_max1 = tl.maximum(max1, block_max1)
        sum_exp1 = sum_exp1 * tl.exp(max1 - new_max1) + tl.sum(tl.exp(tl.where(mask_n, logits1_block, -float('inf')) - new_max1))
        max1 = new_max1
        
        block_max2 = tl.max(tl.where(mask_n, logits2_block, -float('inf')), axis=0)
        new_max2 = tl.maximum(max2, block_max2)
        sum_exp2 = sum_exp2 * tl.exp(max2 - new_max2) + tl.sum(tl.exp(tl.where(mask_n, logits2_block, -float('inf')) - new_max2))
        max2 = new_max2

    lse1 = max1 + tl.log(sum_exp1)
    lse2 = max2 + tl.log(sum_exp2)

    # --- PASS 2: Compute JSD ---
    jsd_sum = 0.0
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n = n_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((1, BLOCK_SIZE_N), dtype=tl.float32)
        acc2 = tl.zeros((1, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            offs_k = k_start * BLOCK_SIZE_K + tl.arange(0, BLOCK_SIZE_K)
            
            x_ptr = x_row_ptr + offs_k * stride_x_k
            x = tl.load(x_ptr, mask=offs_k < K, other=0.0)
            x_mat = tl.reshape(x, (1, BLOCK_SIZE_K))

            w1_ptr = W1_ptr + (offs_k[:, None] * stride_w1_k + offs_n[None, :] * stride_w1_n)
            w1 = tl.load(w1_ptr, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)

            w2_ptr = W2_ptr + (offs_k[:, None] * stride_w2_k + offs_n[None, :] * stride_w2_n)
            w2 = tl.load(w2_ptr, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)

            acc1 += tl.dot(x_mat.to(w1.dtype), w1, out_dtype=tl.float32)
            acc2 += tl.dot(x_mat.to(w2.dtype), w2, out_dtype=tl.float32)

        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)

        logits1_block = tl.squeeze(acc1, axis=0) + b1
        logits2_block = tl.squeeze(acc2, axis=0) + b2

        logp_block = logits1_block - lse1
        logq_block = logits2_block - lse2
        p_block = tl.exp(logp_block)
        q_block = tl.exp(logq_block)
        
        m_block = 0.5 * (p_block + q_block)
        logm_block = tl.log(m_block)
        
        kl_p_term = p_block * (logp_block - logm_block)
        kl_q_term = q_block * (logq_block - logm_block)
        
        kl_p_term = tl.where(p_block > 0, kl_p_term, 0.0)
        kl_q_term = tl.where(q_block > 0, kl_q_term, 0.0)
        
        jsd_sum += tl.sum(tl.where(mask_n, kl_p_term + kl_q_term, 0.0))
        
    jsd = 0.5 * jsd_sum
    
    out_ptr_row = Out_ptr + pid_m * stride_out_m
    tl.store(out_ptr_row, jsd)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _ , N = W1.shape

    output = torch.empty(M, device=X.device, dtype=torch.float32)

    grid = lambda meta: (M,)
    
    _fused_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        output.stride(0),
    )
    return output
"""
        return {"code": code}