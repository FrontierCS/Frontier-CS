import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def linear_fwd_kernel(
    X_ptr, W_ptr, B_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_outm, stride_outn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
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

    x_ptrs = X_ptr + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_bn[None, :] * stride_wn)

    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, tl.cdiv(K, BLOCK_K)):
        x = tl.load(x_ptrs, mask=offs_k[None, :] < K - k * BLOCK_K, other=0.0)
        w = tl.load(w_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        accumulator = tl.dot(x, w, accumulator)
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    b_ptrs = B_ptr + offs_bn
    bias = tl.load(b_ptrs, mask=offs_bn < N, other=0.0)
    accumulator = accumulator + bias[None, :]

    out_ptrs = Out_ptr + (offs_am[:, None] * stride_outm + offs_bn[None, :] * stride_outn)
    mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)
    tl.store(out_ptrs, accumulator, mask=mask)

@triton.jit
def jsd_kernel(
    L1_ptr, L2_ptr, Out_ptr,
    M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    
    row_l1_ptr = L1_ptr + pid_m * stride_l1m
    row_l2_ptr = L2_ptr + pid_m * stride_l2m
    
    m1 = -float('inf')
    d1 = 0.0
    m2 = -float('inf')
    d2 = 0.0
    
    for off_n in range(0, N, BLOCK_N):
        cols = off_n + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        l1 = tl.load(row_l1_ptr + cols, mask=mask, other=-float('inf'))
        l2 = tl.load(row_l2_ptr + cols, mask=mask, other=-float('inf'))
        
        block_max1 = tl.max(l1)
        new_m1 = tl.maximum(m1, block_max1)
        d1 = d1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(l1 - new_m1))
        m1 = new_m1
        
        block_max2 = tl.max(l2)
        new_m2 = tl.maximum(m2, block_max2)
        d2 = d2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(l2 - new_m2))
        m2 = new_m2

    lse1 = m1 + tl.log(d1)
    lse2 = m2 + tl.log(d2)
    
    jsd_sum = 0.0
    
    for off_n in range(0, N, BLOCK_N):
        cols = off_n + tl.arange(0, BLOCK_N)
        mask = cols < N
        
        l1 = tl.load(row_l1_ptr + cols, mask=mask, other=0.0)
        l2 = tl.load(row_l2_ptr + cols, mask=mask, other=0.0)
        
        p = tl.exp(l1 - lse1)
        q = tl.exp(l2 - lse2)
        
        p = tl.where(mask, p, 0.0)
        q = tl.where(mask, q, 0.0)
        
        m_val = 0.5 * (p + q)
        log_m = tl.log(tl.maximum(m_val, 1e-20)) 
        
        term = p * (l1 - lse1 - log_m) + q * (l2 - lse2 - log_m)
        jsd_sum += tl.sum(term)
        
    jsd = 0.5 * jsd_sum
    tl.store(Out_ptr + pid_m, jsd)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    
    Logits1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    Logits2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    JSD = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    linear_fwd_kernel[grid](
        X, W1, B1, Logits1,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        Logits1.stride(0), Logits1.stride(1)
    )
    
    linear_fwd_kernel[grid](
        X, W2, B2, Logits2,
        M, N, K,
        X.stride(0), X.stride(1),
        W2.stride(0), W2.stride(1),
        Logits2.stride(0), Logits2.stride(1)
    )
    
    BLOCK_N_JSD = 2048
    grid_jsd = (M, )
    jsd_kernel[grid_jsd](
        Logits1, Logits2, JSD,
        M, N,
        Logits1.stride(0), Logits1.stride(1),
        Logits2.stride(0), Logits2.stride(1),
        BLOCK_N=BLOCK_N_JSD
    )
    
    return JSD
"""
        }
