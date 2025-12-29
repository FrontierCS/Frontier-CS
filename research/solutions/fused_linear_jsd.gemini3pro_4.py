import torch
import triton
import triton.language as tl
import sys
import inspect

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def dual_linear_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    L1_ptr, L2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr
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

    offs_m = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_n = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w1_ptrs = W1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    w2_ptrs = W2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

    accumulator1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    accumulator2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        mask_k = offs_k[None, :] < K - k * BLOCK_K
        
        x = tl.load(x_ptrs, mask=mask_k, other=0.0)
        
        # Load weights
        # Mask for weights depends on K dimension (rows of W)
        w_mask_k = offs_k[:, None] < K - k * BLOCK_K
        
        w1 = tl.load(w1_ptrs, mask=w_mask_k, other=0.0)
        w2 = tl.load(w2_ptrs, mask=w_mask_k, other=0.0)
        
        accumulator1 = tl.dot(x, w1, accumulator1)
        accumulator2 = tl.dot(x, w2, accumulator2)
        
        x_ptrs += BLOCK_K * stride_xk
        w1_ptrs += BLOCK_K * stride_w1k
        w2_ptrs += BLOCK_K * stride_w2k

    # Add bias
    b1_ptrs = B1_ptr + offs_n
    b2_ptrs = B2_ptr + offs_n
    mask_n_load = offs_n < N
    b1 = tl.load(b1_ptrs, mask=mask_n_load, other=0.0)
    b2 = tl.load(b2_ptrs, mask=mask_n_load, other=0.0)
    
    accumulator1 = accumulator1 + b1[None, :]
    accumulator2 = accumulator2 + b2[None, :]
    
    # Store result
    l1_ptrs = L1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l2_ptrs = L2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)
    
    mask_m = offs_m[:, None] < M
    mask_n = offs_n[None, :] < N
    mask = mask_m & mask_n
    
    tl.store(l1_ptrs, accumulator1, mask=mask)
    tl.store(l2_ptrs, accumulator2, mask=mask)

@triton.jit
def jsd_kernel(
    L1_ptr, L2_ptr, Out_ptr,
    M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N: tl.constexpr
):
    row_idx = tl.program_id(0)
    
    l1_row_ptr = L1_ptr + row_idx * stride_l1m
    l2_row_ptr = L2_ptr + row_idx * stride_l2m
    
    # Pass 1: Compute LogSumExp for both rows
    m1 = -float('inf')
    s1 = 0.0
    m2 = -float('inf')
    s2 = 0.0
    
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        # Load logits
        v1 = tl.load(l1_row_ptr + cols * stride_l1n, mask=mask, other=-float('inf'))
        v2 = tl.load(l2_row_ptr + cols * stride_l2n, mask=mask, other=-float('inf'))
        
        # Online Softmax 1
        vm1 = tl.max(v1)
        new_m1 = tl.maximum(m1, vm1)
        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(v1 - new_m1))
        m1 = new_m1
        
        # Online Softmax 2
        vm2 = tl.max(v2)
        new_m2 = tl.maximum(m2, vm2)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(v2 - new_m2))
        m2 = new_m2

    # Pass 2: Compute JSD terms
    jsd_sum = 0.0
    
    for off in range(0, N, BLOCK_N):
        cols = off + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        # Load logits again. Use -inf to ensure exp() is 0 for masked elements
        v1 = tl.load(l1_row_ptr + cols * stride_l1n, mask=mask, other=-float('inf'))
        v2 = tl.load(l2_row_ptr + cols * stride_l2n, mask=mask, other=-float('inf'))
        
        p = tl.exp(v1 - m1) / s1
        q = tl.exp(v2 - m2) / s2
        
        # m = 0.5 * (p + q)
        m_dist = 0.5 * (p + q)
        
        # KL(P||M) = P * (log P - log M)
        # log P = v1 - m1 - log(s1)
        log_p = v1 - m1 - tl.log(s1)
        log_q = v2 - m2 - tl.log(s2)
        
        # log M = log(m_dist). Add epsilon for safety when p=q=0
        log_m = tl.log(m_dist + 1e-20)
        
        # Compute terms, masking out zero probabilities to avoid 0*-inf
        t1 = tl.where(p > 0, p * (log_p - log_m), 0.0)
        t2 = tl.where(q > 0, q * (log_q - log_m), 0.0)
        
        jsd_sum += tl.sum(0.5 * (t1 + t2))
        
    tl.store(Out_ptr + row_idx, jsd_sum)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    M, K = X.shape
    _, N = W1.shape
    
    # Allocate intermediate logits in float32 for precision
    L1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    L2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    
    # 1. Dual Linear Layer Kernel
    grid_linear = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    dual_linear_kernel[grid_linear](
        X, W1, B1, W2, B2,
        L1, L2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1)
    )
    
    # 2. Fused JSD Kernel
    JSD = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Use a large BLOCK_N to minimize loops, 2048 covers typical vocab size efficiently in 2-4 iterations
    BLOCK_N_JSD = 2048
    grid_jsd = (M,)
    jsd_kernel[grid_jsd](
        L1, L2, JSD,
        M, N,
        L1.stride(0), L1.stride(1),
        L2.stride(0), L2.stride(1),
        BLOCK_N=BLOCK_N_JSD,
        num_warps=8
    )
    
    return JSD

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": inspect.getsource(sys.modules[__name__])}