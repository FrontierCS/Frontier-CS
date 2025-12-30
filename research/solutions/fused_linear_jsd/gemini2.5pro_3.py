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
        # Basic configurations, balanced tile sizes
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 4, 'num_warps': 8}),
        
        # Wider N-tile configs
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),

        # Deeper K-tile config
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 8}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_ym,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    # This kernel assumes that K and N are perfectly divisible by BLOCK_K and BLOCK_N.
    # This holds true for the problem constraints and chosen autotuner configs.
    
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Pass 1: Compute Log-Sum-Exp for both branches
    m1 = tl.full([BLOCK_M], value=float('-inf'), dtype=tl.float32)
    s1 = tl.zeros([BLOCK_M], dtype=tl.float32)
    m2 = tl.full([BLOCK_M], value=float('-inf'), dtype=tl.float32)
    s2 = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    offs_k = tl.arange(0, BLOCK_K)

    for n_idx in range(0, tl.cdiv(N, BLOCK_N)):
        n_start = n_idx * BLOCK_N
        offs_n = n_start + tl.arange(0, BLOCK_N)

        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        for k_idx in range(0, tl.cdiv(K, BLOCK_K)):
            k_start = k_idx * BLOCK_K
            cur_offs_k = k_start + offs_k
            
            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + cur_offs_k[None, :] * stride_xk
            x = tl.load(x_ptrs, mask=mask_m[:, None], other=0.0)
            
            w1_ptrs = W1_ptr + cur_offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
            w1 = tl.load(w1_ptrs)
            
            w2_ptrs = W2_ptr + cur_offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
            w2 = tl.load(w2_ptrs)
            
            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        b1_ptrs = B1_ptr + offs_n
        b1 = tl.load(b1_ptrs)
        logits1 = acc1 + b1[None, :]

        b2_ptrs = B2_ptr + offs_n
        b2 = tl.load(b2_ptrs)
        logits2 = acc2 + b2[None, :]

        # Update running max and sum for LSE using stable online algorithm
        tile_m1 = tl.max(logits1, axis=1)
        new_m1 = tl.maximum(m1, tile_m1)
        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(logits1 - new_m1[:, None]), axis=1)
        m1 = new_m1
        
        tile_m2 = tl.max(logits2, axis=1)
        new_m2 = tl.maximum(m2, tile_m2)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(logits2 - new_m2[:, None]), axis=1)
        m2 = new_m2

    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)

    # Pass 2: Compute JSD by recomputing logits
    jsd = tl.zeros([BLOCK_M], dtype=tl.float32)
    LOG_HALF = -0.6931471805599453

    for n_idx in range(0, tl.cdiv(N, BLOCK_N)):
        n_start = n_idx * BLOCK_N
        offs_n = n_start + tl.arange(0, BLOCK_N)

        # Recompute logits to save memory vs storing them
        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k_idx in range(0, tl.cdiv(K, BLOCK_K)):
            k_start = k_idx * BLOCK_K
            cur_offs_k = k_start + offs_k

            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + cur_offs_k[None, :] * stride_xk
            x = tl.load(x_ptrs, mask=mask_m[:, None], other=0.0)
            
            w1_ptrs = W1_ptr + cur_offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
            w1 = tl.load(w1_ptrs)
            
            w2_ptrs = W2_ptr + cur_offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
            w2 = tl.load(w2_ptrs)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)
        
        b1_ptrs = B1_ptr + offs_n
        b1 = tl.load(b1_ptrs)
        logits1 = acc1 + b1[None, :]

        b2_ptrs = B2_ptr + offs_n
        b2 = tl.load(b2_ptrs)
        logits2 = acc2 + b2[None, :]

        log_p = logits1 - lse1[:, None]
        log_q = logits2 - lse2[:, None]

        p = tl.exp(log_p)
        q = tl.exp(log_q)

        # Stable computation of log(0.5 * (p + q))
        max_log_pq = tl.maximum(log_p, log_q)
        log_sum_exp_pq = max_log_pq + tl.log(tl.exp(log_p - max_log_pq) + tl.exp(log_q - max_log_pq))
        log_m = LOG_HALF + log_sum_exp_pq
        
        kl_p = p * (log_p - log_m)
        kl_q = q * (log_q - log_m)
        
        # Handle cases where p or q are 0
        kl_p = tl.where(p > 0, kl_p, 0.0)
        kl_q = tl.where(q > 0, kl_q, 0.0)

        jsd_tile = 0.5 * (kl_p + kl_q)
        jsd += tl.sum(jsd_tile, axis=1)

    y_ptrs = Y_ptr + offs_m * stride_ym
    tl.store(y_ptrs, jsd, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape

    Y = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Grid is 1D, covering the M dimension
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']),)
    
    _fused_jsd_kernel[grid](
        X, W1, B1, W2, B2, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        Y.stride(0),
    )
    return Y
"""
        return {"code": code}