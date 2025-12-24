import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

AUTOTUNER_CONFIGS = [
    # Basic configs
    triton.Config({'BLOCK_N': 512, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_N': 1024, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_N': 2048, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_N': 4096, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_N': 1024, 'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 8}),
    triton.Config({'BLOCK_N': 512, 'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 8}),
    # More aggressive configs
    triton.Config({'BLOCK_N': 2048, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
    triton.Config({'BLOCK_N': 4096, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 8}),
    # Large block N configs
    triton.Config({'BLOCK_N': 4096, 'BLOCK_K': 16, 'num_stages': 4, 'num_warps': 4}),
    triton.Config({'BLOCK_N': 4096, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
]

@triton.autotune(
    configs=AUTOTUNER_CONFIGS,
    key=['N', 'K'],
)
@triton.jit
def _jsd_lse_kernel(
    X, W1, B1, W2, B2, LSE1, LSE2,
    stride_x_m, stride_x_k,
    stride_w1_k, stride_w1_n,
    stride_w2_k, stride_w2_n,
    M, N, K,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)

    # Online reduction state for LSE
    row_max1 = -float('inf')
    row_sum_exp1 = 0.0
    row_max2 = -float('inf')
    row_sum_exp2 = 0.0

    # Loop over N in blocks
    for n_offset in range(0, N, BLOCK_N):
        n_block_range = tl.arange(0, BLOCK_N)
        n_block = n_offset + n_block_range
        n_mask = n_block < N

        # Accumulators for logits
        acc1 = tl.zeros((1, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((1, BLOCK_N), dtype=tl.float32)

        # Loop over K in blocks to compute dot product
        for k_offset in range(0, K, BLOCK_K):
            k_block_range = tl.arange(0, BLOCK_K)
            k_block = k_offset + k_block_range
            k_mask = k_block < K

            # Load X tile (1, BLOCK_K)
            x_ptrs = X + pid_m * stride_x_m + k_block[None, :]
            x_tile = tl.load(x_ptrs, mask=k_mask[None, :], other=0.0)

            # Load W tiles (BLOCK_K, BLOCK_N)
            w1_ptrs = W1 + k_block[:, None] * stride_w1_k + n_block[None, :] * stride_w1_n
            w2_ptrs = W2 + k_block[:, None] * stride_w2_k + n_block[None, :] * stride_w2_n
            
            w1_tile = tl.load(w1_ptrs, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            w2_tile = tl.load(w2_ptrs, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)

            # Accumulate using Tensor Cores
            acc1 += tl.dot(x_tile, w1_tile, out_dtype=tl.float32)
            acc2 += tl.dot(x_tile, w2_tile, out_dtype=tl.float32)

        # Add bias
        b1_ptrs = B1 + n_block
        b2_ptrs = B2 + n_block
        b1 = tl.load(b1_ptrs, mask=n_mask, other=0.0)
        b2 = tl.load(b2_ptrs, mask=n_mask, other=0.0)

        logits1_tile = acc1 + b1
        logits2_tile = acc2 + b2

        # Mask out-of-bounds logits for reduction
        logits1_tile = tl.where(n_mask[None, :], logits1_tile, -float('inf'))
        logits2_tile = tl.where(n_mask[None, :], logits2_tile, -float('inf'))
        
        # --- Online LSE Reduction for this tile ---
        tile_max1 = tl.max(logits1_tile, axis=1)
        new_max1 = tl.maximum(row_max1, tile_max1)
        row_sum_exp1 = row_sum_exp1 * tl.exp(row_max1 - new_max1) + tl.sum(tl.exp(logits1_tile - new_max1), axis=1)
        row_max1 = new_max1

        tile_max2 = tl.max(logits2_tile, axis=1)
        new_max2 = tl.maximum(row_max2, tile_max2)
        row_sum_exp2 = row_sum_exp2 * tl.exp(row_max2 - new_max2) + tl.sum(tl.exp(logits2_tile - new_max2), axis=1)
        row_max2 = new_max2

    # Finalize LSE
    lse1 = row_max1 + tl.log(row_sum_exp1)
    lse2 = row_max2 + tl.log(row_sum_exp2)

    # Store results
    tl.store(LSE1 + pid_m, lse1)
    tl.store(LSE2 + pid_m, lse2)


@triton.autotune(
    configs=AUTOTUNER_CONFIGS,
    key=['N', 'K'],
)
@triton.jit
def _jsd_calc_kernel(
    X, W1, B1, W2, B2, LSE1, LSE2, JSD,
    stride_x_m, stride_x_k,
    stride_w1_k, stride_w1_n,
    stride_w2_k, stride_w2_n,
    M, N, K,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)

    # Load LSE for the current row
    lse1 = tl.load(LSE1 + pid_m)
    lse2 = tl.load(LSE2 + pid_m)

    # Accumulator for JSD
    jsd_sum = 0.0

    # Loop over N in blocks
    for n_offset in range(0, N, BLOCK_N):
        n_block_range = tl.arange(0, BLOCK_N)
        n_block = n_offset + n_block_range
        n_mask = n_block < N

        # Recompute logits tile (same as first kernel)
        acc1 = tl.zeros((1, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((1, BLOCK_N), dtype=tl.float32)
        for k_offset in range(0, K, BLOCK_K):
            k_block_range = tl.arange(0, BLOCK_K)
            k_block = k_offset + k_block_range
            k_mask = k_block < K
            
            x_ptrs = X + pid_m * stride_x_m + k_block[None, :]
            x_tile = tl.load(x_ptrs, mask=k_mask[None, :], other=0.0)

            w1_ptrs = W1 + k_block[:, None] * stride_w1_k + n_block[None, :] * stride_w1_n
            w2_ptrs = W2 + k_block[:, None] * stride_w2_k + n_block[None, :] * stride_w2_n

            w1_tile = tl.load(w1_ptrs, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            w2_tile = tl.load(w2_ptrs, mask=(k_mask[:, None] & n_mask[None, :]), other=0.0)
            
            acc1 += tl.dot(x_tile, w1_tile, out_dtype=tl.float32)
            acc2 += tl.dot(x_tile, w2_tile, out_dtype=tl.float32)

        b1_ptrs = B1 + n_block
        b2_ptrs = B2 + n_block
        b1 = tl.load(b1_ptrs, mask=n_mask, other=0.0)
        b2 = tl.load(b2_ptrs, mask=n_mask, other=0.0)
        logits1_tile = acc1 + b1
        logits2_tile = acc2 + b2

        # --- JSD Calculation for this tile ---
        log_p_tile = logits1_tile - lse1
        log_q_tile = logits2_tile - lse2
        p_tile = tl.exp(log_p_tile)
        q_tile = tl.exp(log_q_tile)
        
        m_tile = 0.5 * (p_tile + q_tile)
        # Add epsilon for numerical stability of log
        log_m_tile = tl.log(m_tile + 1e-9) 
        
        kl_p_term = p_tile * (log_p_tile - log_m_tile)
        kl_q_term = q_tile * (log_q_tile - log_m_tile)
        
        jsd_tile = 0.5 * (kl_p_term + kl_q_term)
        jsd_tile = tl.where(n_mask[None, :], jsd_tile, 0.0)
        
        jsd_sum += tl.sum(jsd_tile, axis=1)

    # Store final JSD for the row
    tl.store(JSD + pid_m, jsd_sum)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _K, N = W1.shape
    
    # Allocate intermediate and output tensors
    LSE1 = torch.empty((M,), dtype=torch.float32, device='cuda')
    LSE2 = torch.empty((M,), dtype=torch.float32, device='cuda')
    JSD = torch.empty((M,), dtype=torch.float32, device='cuda')

    # Grid of M programs, one for each row of X
    grid = lambda META: (M, )

    # Pass 1: Compute log-sum-exp for both branches
    _jsd_lse_kernel[grid](
        X, W1, B1, W2, B2, LSE1, LSE2,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        M, N, K
    )

    # Pass 2: Recompute logits and compute JSD
    _jsd_calc_kernel[grid](
        X, W1, B1, W2, B2, LSE1, LSE2, JSD,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        M, N, K
    )

    return JSD
"""
        return {"code": kernel_code}
