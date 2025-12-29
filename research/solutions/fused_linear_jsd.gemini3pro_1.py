import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path=None):
        return {"code": r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 128, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_gemm_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    L1_ptr, L2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_SIZE_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers
    x_ptrs = X_ptr + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_bn[None, :] * stride_w1n)
    w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_bn[None, :] * stride_w2n)

    # Accumulators
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Load X - reused for both W1 and W2
        x = tl.load(x_ptrs, mask=offs_k[None, :] < K - k * BLOCK_K, other=0.0)
        
        # Load W1, W2
        w1 = tl.load(w1_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        w2 = tl.load(w2_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        
        # Compute
        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)
        
        # Advance
        x_ptrs += BLOCK_K * stride_xk
        w1_ptrs += BLOCK_K * stride_w1k
        w2_ptrs += BLOCK_K * stride_w2k

    # Add bias
    b1_ptrs = B1_ptr + offs_bn
    b2_ptrs = B2_ptr + offs_bn
    b1 = tl.load(b1_ptrs, mask=offs_bn < N, other=0.0)
    b2 = tl.load(b2_ptrs, mask=offs_bn < N, other=0.0)
    
    acc1 += b1[None, :]
    acc2 += b2[None, :]

    # Store L1, L2
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    l1_ptrs = L1_ptr + stride_l1m * offs_cm[:, None] + stride_l1n * offs_cn[None, :]
    l2_ptrs = L2_ptr + stride_l2m * offs_cm[:, None] + stride_l2n * offs_cn[None, :]
    
    mask_m = offs_cm[:, None] < M
    mask_n = offs_cn[None, :] < N
    
    tl.store(l1_ptrs, acc1, mask=mask_m & mask_n)
    tl.store(l2_ptrs, acc2, mask=mask_m & mask_n)

@triton.jit
def jsd_kernel(
    L1_ptr, L2_ptr, Out_ptr,
    M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N: tl.constexpr
):
    # Each program handles one row
    row_idx = tl.program_id(0)
    
    # Pointers to the row start
    l1_row_ptr = L1_ptr + row_idx * stride_l1m
    l2_row_ptr = L2_ptr + row_idx * stride_l2m
    
    # Pass 1: Max and SumExp
    m1 = -float('inf')
    m2 = -float('inf')
    s1 = 0.0
    s2 = 0.0
    
    # Iterate over N to find max
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        val1 = tl.load(l1_row_ptr + cols * stride_l1n, mask=mask, other=-float('inf'))
        val2 = tl.load(l2_row_ptr + cols * stride_l2n, mask=mask, other=-float('inf'))
        
        m1 = tl.maximum(m1, tl.max(val1, 0))
        m2 = tl.maximum(m2, tl.max(val2, 0))
    
    # Iterate over N to compute sum exp
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        val1 = tl.load(l1_row_ptr + cols * stride_l1n, mask=mask, other=-float('inf'))
        val2 = tl.load(l2_row_ptr + cols * stride_l2n, mask=mask, other=-float('inf'))
        
        s1 += tl.sum(tl.exp(val1 - m1), 0)
        s2 += tl.sum(tl.exp(val2 - m2), 0)
        
    # Pass 2: Compute JSD
    # JSD = 0.5 * sum(P * (logP - logM) + Q * (logQ - logM))
    # where M = 0.5(P+Q)
    
    jsd_sum = 0.0
    
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        l1 = tl.load(l1_row_ptr + cols * stride_l1n, mask=mask, other=0.0)
        l2 = tl.load(l2_row_ptr + cols * stride_l2n, mask=mask, other=0.0)
        
        p = tl.exp(l1 - m1) / s1
        q = tl.exp(l2 - m2) / s2
        
        # Mask out padded values to avoid NaN in log
        p = tl.where(mask, p, 0.0)
        q = tl.where(mask, q, 0.0)
        
        m = 0.5 * (p + q)
        
        # KL terms: P * log(P/M) + Q * log(Q/M)
        # Safe log: if p=0, p*log(p)=0.
        term1 = tl.where(p > 0, p * (tl.log(p) - tl.log(m)), 0.0)
        term2 = tl.where(q > 0, q * (tl.log(q) - tl.log(m)), 0.0)
        
        jsd_sum += tl.sum(0.5 * term1 + 0.5 * term2, 0)

    tl.store(Out_ptr + row_idx, jsd_sum)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    
    # Output buffers
    # Use float32 for logits to ensure stability and accumulated precision
    L1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    L2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    JSD = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # 1. Fused GEMM: Computes XW1+B1 and XW2+B2 in one kernel launch
    grid_gemm = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )
    
    fused_gemm_kernel[grid_gemm](
        X, W1, B1, W2, B2,
        L1, L2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1),
    )
    
    # 2. JSD Reduction: Row-wise reduction kernel
    BLOCK_N = 1024
    grid_jsd = (M,)
    
    jsd_kernel[grid_jsd](
        L1, L2, JSD,
        M, N,
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1),
        BLOCK_N=BLOCK_N,
        num_warps=4
    )
    
    return JSD
"""}