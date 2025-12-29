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
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _compute_logits_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, L1_ptr, L2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1, stride_b2,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, BLOCK_K):
        mask_x = (offs_m[:, None] < M) & ((k + offs_k[None, :]) < K)
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)

        mask_w = ((k + offs_k[:, None]) < K) & (offs_n[None, :] < N)
        w1 = tl.load(w1_ptrs, mask=mask_w, other=0.0)
        w2 = tl.load(w2_ptrs, mask=mask_w, other=0.0)

        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)
        
        x_ptrs += BLOCK_K * stride_xk
        w1_ptrs += BLOCK_K * stride_w1k
        w2_ptrs += BLOCK_K * stride_w2k

    b1_ptrs = B1_ptr + offs_n * stride_b1
    b2_ptrs = B2_ptr + offs_n * stride_b2
    mask_b = offs_n < N
    b1 = tl.load(b1_ptrs, mask=mask_b)
    b2 = tl.load(b2_ptrs, mask=mask_b)
    
    l1 = acc1 + b1[None, :]
    l2 = acc2 + b2[None, :]

    l1_ptrs = L1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l2_ptrs = L2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)
    mask_out = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(l1_ptrs, l1, mask=mask_out)
    tl.store(l2_ptrs, l2, mask=mask_out)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N_REDUCE': 512}, num_warps=2),
        triton.Config({'BLOCK_N_REDUCE': 1024}, num_warps=4),
        triton.Config({'BLOCK_N_REDUCE': 2048}, num_warps=8),
        triton.Config({'BLOCK_N_REDUCE': 4096}, num_warps=16),
    ],
    key=['N'],
)
@triton.jit
def _jsd_reduce_kernel(
    L1_ptr, L2_ptr, Y_ptr, M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N_REDUCE: tl.constexpr
):
    pid = tl.program_id(0)
    
    l1_row_ptr = L1_ptr + pid * stride_l1m
    l2_row_ptr = L2_ptr + pid * stride_l2m
    
    # Pass 1: compute Log-Sum-Exp for numerical stability
    m1, m2 = -float('inf'), -float('inf')
    s1, s2 = 0.0, 0.0
    
    for off in range(0, N, BLOCK_N_REDUCE):
        n_indices = off + tl.arange(0, BLOCK_N_REDUCE)
        mask = n_indices < N
        
        l1 = tl.load(l1_row_ptr + n_indices * stride_l1n, mask=mask, other=-float('inf'))
        l2 = tl.load(l2_row_ptr + n_indices * stride_l2n, mask=mask, other=-float('inf'))

        block_m1 = tl.max(l1, 0)
        new_m1 = tl.maximum(m1, block_m1)
        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(l1 - new_m1), 0)
        m1 = new_m1

        block_m2 = tl.max(l2, 0)
        new_m2 = tl.maximum(m2, block_m2)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(l2 - new_m2), 0)
        m2 = new_m2
        
    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)
    
    # Pass 2: compute Jensen-Shannon Divergence
    jsd_sum = 0.0
    LOG2 = 0.6931471805599453
    
    for off in range(0, N, BLOCK_N_REDUCE):
        n_indices = off + tl.arange(0, BLOCK_N_REDUCE)
        mask = n_indices < N
        
        l1 = tl.load(l1_row_ptr + n_indices * stride_l1n, mask=mask, other=-float('inf'))
        l2 = tl.load(l2_row_ptr + n_indices * stride_l2n, mask=mask, other=-float('inf'))

        log_p = l1 - lse1
        log_q = l2 - lse2
        
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        
        max_log_pq = tl.maximum(log_p, log_q)
        # Add epsilon to prevent log(0)
        sum_exp = tl.exp(log_p - max_log_pq) + tl.exp(log_q - max_log_pq) + 1e-9
        log_m = -LOG2 + max_log_pq + tl.log(sum_exp)
        
        kl_pm = p * log_p - p * log_m
        kl_qm = q * log_q - q * log_m
        
        # Handle cases where p or q are 0 to avoid 0 * -inf = nan
        kl_pm = tl.where(p > 0, kl_pm, 0.0)
        kl_qm = tl.where(q > 0, kl_qm, 0.0)
        
        jsd_sum += tl.sum(tl.where(mask, kl_pm + kl_qm, 0.0), 0)

    tl.store(Y_ptr + pid, 0.5 * jsd_sum)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    
    # Intermediate tensors for logits
    logits1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    logits2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    
    # Kernel 1: Compute logits from two linear layers
    grid_logits = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
    _compute_logits_kernel[grid_logits](
        X, W1, B1, W2, B2, logits1, logits2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
    )
    
    # Final output tensor
    Y = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Kernel 2: Reduce logits to compute JSD
    grid_reduce = (M,)
    _jsd_reduce_kernel[grid_reduce](
        logits1, logits2, Y, M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
    )
    
    return Y
"""
        return {"code": code}