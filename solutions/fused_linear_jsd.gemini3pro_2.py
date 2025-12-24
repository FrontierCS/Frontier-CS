import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import os
        return {"code": open(os.path.abspath(__file__)).read()}

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4),
        triton.Config({'BLOCK_M': 32,  'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_gemm_kernel(
    x_ptr, w1_ptr, b1_ptr, w2_ptr, b2_ptr,
    l1_ptr, l2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w1_ptrs = w1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    w2_ptrs = w2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        x_mask = (offs_m[:, None] < M) & (k * BLOCK_K + offs_k[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        
        w_mask = (k * BLOCK_K + offs_k[:, None] < K) & (offs_n[None, :] < N)
        w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0)
        w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0)
        
        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)
        
        x_ptrs += BLOCK_K * stride_xk
        w1_ptrs += BLOCK_K * stride_w1k
        w2_ptrs += BLOCK_K * stride_w2k

    b_mask = offs_n < N
    b1_ptrs = b1_ptr + offs_n
    b2_ptrs = b2_ptr + offs_n
    b1 = tl.load(b1_ptrs, mask=b_mask, other=0.0)
    b2 = tl.load(b2_ptrs, mask=b_mask, other=0.0)
    
    acc1 += b1[None, :]
    acc2 += b2[None, :]
    
    l1_ptrs = l1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l2_ptrs = l2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)
    
    store_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(l1_ptrs, acc1, mask=store_mask)
    tl.store(l2_ptrs, acc2, mask=store_mask)

@triton.jit
def jsd_kernel(
    l1_ptr, l2_ptr, out_ptr,
    stride_m, N,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    cols = tl.arange(0, BLOCK_N)
    
    offset = pid * stride_m + cols
    mask = cols < N
    
    # Load logits with -inf padding for max/exp calculation
    l1 = tl.load(l1_ptr + offset, mask=mask, other=-float('inf'))
    l2 = tl.load(l2_ptr + offset, mask=mask, other=-float('inf'))
    
    # Max for stability
    m1 = tl.max(l1, axis=0)
    m2 = tl.max(l2, axis=0)
    
    # Sum of exponentials
    e1 = tl.exp(l1 - m1)
    e2 = tl.exp(l2 - m2)
    s1 = tl.sum(e1, axis=0)
    s2 = tl.sum(e2, axis=0)
    
    # LogSumExp
    z1 = m1 + tl.log(s1)
    z2 = m2 + tl.log(s2)
    
    # Probabilities
    p = e1 / s1
    q = e2 / s2
    
    sum_pq = p + q
    
    # Safe l1/l2 for term calculation (avoid NaN from 0 * -inf)
    l1_safe = tl.where(mask, l1, 0.0)
    l2_safe = tl.where(mask, l2, 0.0)
    
    # Safe log(sum_pq)
    log_sum_pq = tl.log(sum_pq + 1e-20)
    
    term1 = p * (l1_safe - z1)
    term2 = q * (l2_safe - z2)
    term3 = sum_pq * log_sum_pq
    
    total = term1 + term2 - term3
    
    # Mask invalid elements
    total = tl.where(mask, total, 0.0)
    
    res_sum = tl.sum(total, axis=0)
    
    # JSD = 0.5 * sum + log(2)
    jsd = 0.5 * res_sum + 0.69314718056
    
    tl.store(out_ptr + pid, jsd)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    
    # Allocate intermediate logits in float32 for precision
    l1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    l2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    
    # 1. Fused Linear Pass
    grid_linear = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N'])
    )
    
    fused_gemm_kernel[grid_linear](
        X, W1, B1, W2, B2,
        l1, l2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        l1.stride(0), l1.stride(1),
        l2.stride(0), l2.stride(1)
    )
    
    # 2. JSD Pass
    out = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Use next power of 2 for BLOCK_N to cover N without loop
    # N is typically 4096, which fits in one block
    block_n = triton.next_power_of_2(N)
    
    # JSD kernel computes one row per block
    jsd_kernel[(M,)](
        l1, l2, out,
        l1.stride(0), N,
        BLOCK_N=block_n,
        num_warps=8
    )
    
    return out
