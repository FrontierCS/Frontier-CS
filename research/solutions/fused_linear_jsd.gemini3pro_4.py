import torch
import triton
import triton.language as tl
import sys
import inspect

# Fused Linear Kernel: Computes X @ W1 + B1 and X @ W2 + B2
@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_kernel(
    x_ptr, w1_ptr, b1_ptr, w2_ptr, b2_ptr,
    l1_ptr, l2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers
    x_ptrs = x_ptr + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w1_ptrs = w1_ptr + (offs_k[:, None] * stride_w1k + offs_bn[None, :] * stride_w1n)
    w2_ptrs = w2_ptr + (offs_k[:, None] * stride_w2k + offs_bn[None, :] * stride_w2n)

    # Accumulators
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Load X - reuse for both W1 and W2
        x = tl.load(x_ptrs, mask=offs_k[None, :] < K - k * BLOCK_K, other=0.0)
        
        # Load W1
        w1 = tl.load(w1_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        acc1 += tl.dot(x, w1)
        
        # Load W2
        w2 = tl.load(w2_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        acc2 += tl.dot(x, w2)
        
        # Advance pointers
        x_ptrs += BLOCK_K * stride_xk
        w1_ptrs += BLOCK_K * stride_w1k
        w2_ptrs += BLOCK_K * stride_w2k

    # Add bias
    b1_ptrs = b1_ptr + offs_bn
    b2_ptrs = b2_ptr + offs_bn
    b1 = tl.load(b1_ptrs, mask=offs_bn < N, other=0.0)
    b2 = tl.load(b2_ptrs, mask=offs_bn < N, other=0.0)
    
    acc1 += b1[None, :]
    acc2 += b2[None, :]

    # Store
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    l1_ptrs = l1_ptr + stride_l1m * offs_cm[:, None] + stride_l1n * offs_cn[None, :]
    l2_ptrs = l2_ptr + stride_l2m * offs_cm[:, None] + stride_l2n * offs_cn[None, :]
    
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    
    tl.store(l1_ptrs, acc1, mask=c_mask)
    tl.store(l2_ptrs, acc2, mask=c_mask)

# JSD Kernel: Computes JSD from logits
@triton.jit
def jsd_kernel(
    l1_ptr, l2_ptr, out_ptr,
    N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    row_l1 = l1_ptr + pid * stride_l1m
    row_l2 = l2_ptr + pid * stride_l2m
    
    # 1. Compute Max for numerical stability
    m1 = -float('inf')
    m2 = -float('inf')
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        val1 = tl.load(row_l1 + cols * stride_l1n, mask=mask, other=-float('inf'))
        val2 = tl.load(row_l2 + cols * stride_l2n, mask=mask, other=-float('inf'))
        m1 = tl.maximum(m1, tl.max(val1, 0))
        m2 = tl.maximum(m2, tl.max(val2, 0))
    
    # 2. Compute Sum Exp
    s1 = 0.0
    s2 = 0.0
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        val1 = tl.load(row_l1 + cols * stride_l1n, mask=mask, other=-float('inf'))
        val2 = tl.load(row_l2 + cols * stride_l2n, mask=mask, other=-float('inf'))
        s1 += tl.sum(tl.exp(val1 - m1), 0)
        s2 += tl.sum(tl.exp(val2 - m2), 0)
        
    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)
    
    # 3. Accumulate JSD
    # JSD = 0.5 * KL(P||M) + 0.5 * KL(Q||M)
    # KL(P||M) = sum P * (log P - log M)
    # log M = log(0.5) + logaddexp(log P, log Q)
    
    jsd_acc = 0.0
    log_05 = -0.69314718056 # log(0.5)
    
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        val1 = tl.load(row_l1 + cols * stride_l1n, mask=mask, other=-float('inf'))
        val2 = tl.load(row_l2 + cols * stride_l2n, mask=mask, other=-float('inf'))
        
        # log probabilities
        log_p = val1 - lse1
        log_q = val2 - lse2
        
        # log M computation
        # logaddexp(x, y) = max + log(exp(x-max) + exp(y-max))
        max_log = tl.maximum(log_p, log_q)
        term_sum = tl.exp(log_p - max_log) + tl.exp(log_q - max_log)
        log_m = log_05 + max_log + tl.log(term_sum)
        
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        
        # KL terms
        term_p = p * (log_p - log_m)
        term_q = q * (log_q - log_m)
        
        # Masking
        term_p = tl.where(mask, term_p, 0.0)
        term_q = tl.where(mask, term_q, 0.0)
        
        jsd_acc += tl.sum(term_p + term_q, 0)
        
    tl.store(out_ptr + pid, 0.5 * jsd_acc)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    M, K = X.shape
    _, N = W1.shape
    
    # Check constraints and contiguous
    X = X.contiguous()
    W1 = W1.contiguous()
    W2 = W2.contiguous()
    B1 = B1.contiguous()
    B2 = B2.contiguous()
    
    # Alloc logits
    logits1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    logits2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    
    # Launch Linear Kernel
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    fused_linear_kernel[grid](
        X, W1, B1, W2, B2,
        logits1, logits2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
    )
    
    # Alloc Output
    jsd_out = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Launch JSD Kernel
    # Block size N can be static or heuristic
    BLOCK_N = 1024
    if N > 4096:
        BLOCK_N = 2048
        
    grid_jsd = (M,)
    jsd_kernel[grid_jsd](
        logits1, logits2, jsd_out,
        N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_N=BLOCK_N
    )
    
    return jsd_out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": inspect.getsource(sys.modules[__name__])}
