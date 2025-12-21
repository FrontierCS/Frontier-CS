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
        triton.Config({'BLOCK_M': 16, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_K': 128, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def linear_ce_fwd_kernel(
    X_ptr, W_ptr, B_ptr, Targets_ptr,
    Max_ptr, Sum_ptr, Target_Logits_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
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
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    m_mask = offs_m < M
    
    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    b_ptrs = B_ptr + offs_n
    
    bias = tl.load(b_ptrs)
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        x = tl.load(x_ptrs, mask=m_mask[:, None], other=0.0)
        w = tl.load(w_ptrs)
        accumulator += tl.dot(x, w)
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
        
    logits = accumulator + bias[None, :]
    
    local_max = tl.max(logits, axis=1)
    # Numerical stability: sum(exp(x - max))
    local_sum = tl.sum(tl.exp(logits - local_max[:, None]), axis=1)
    
    t_ptrs = Targets_ptr + offs_m
    targets = tl.load(t_ptrs, mask=m_mask, other=-1)
    
    # Check if targets are in range [n_start, n_start + BLOCK_N)
    # offs_n is (1, BLOCK_N)
    target_in_block = (targets[:, None] == offs_n[None, :])
    
    # Reduction along axis 1 to see if target was found in this block
    found_rows = tl.sum(target_in_block.to(tl.int32), axis=1)
    
    # Extract values
    masked_logits = logits * target_in_block.to(tl.float32)
    target_val = tl.sum(masked_logits, axis=1)
    
    # Store where found
    target_logits_ptrs = Target_Logits_ptr + offs_m
    store_mask = m_mask & (found_rows > 0)
    tl.store(target_logits_ptrs, target_val, mask=store_mask)
    
    # Store Max and Sum
    out_idx = offs_m * num_pid_n + pid_n
    tl.store(Max_ptr + out_idx, local_max, mask=m_mask)
    tl.store(Sum_ptr + out_idx, local_sum, mask=m_mask)

@triton.jit
def reduction_kernel(
    Max_ptr, Sum_ptr, Target_Logits_ptr,
    Loss_ptr,
    M, Num_Blocks_N,
    BLOCK_M: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    target_logit = tl.load(Target_Logits_ptr + offs_m, mask=mask_m, other=0.0)
    
    global_max = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    
    # Pass 1: Global Max
    for i in range(Num_Blocks_N):
        idx = offs_m * Num_Blocks_N + i
        val = tl.load(Max_ptr + idx, mask=mask_m, other=float('-inf'))
        global_max = tl.max(global_max, val)
        
    # Pass 2: Sum Exp
    total_sum = tl.zeros((BLOCK_M,), dtype=tl.float32)
    for i in range(Num_Blocks_N):
        idx = offs_m * Num_Blocks_N + i
        m_val = tl.load(Max_ptr + idx, mask=mask_m, other=float('-inf'))
        s_val = tl.load(Sum_ptr + idx, mask=mask_m, other=0.0)
        total_sum += s_val * tl.exp(m_val - global_max)
        
    loss = -target_logit + global_max + tl.log(total_sum)
    tl.store(Loss_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K2, N = W.shape
    assert K == K2
    
    # Fix BLOCK_N to 128 for simplicity and efficiency
    BN = 128
    num_blocks_n = (N + BN - 1) // BN
    
    max_buffer = torch.empty((M, num_blocks_n), dtype=torch.float32, device=X.device)
    sum_buffer = torch.empty((M, num_blocks_n), dtype=torch.float32, device=X.device)
    target_logits = torch.empty((M,), dtype=torch.float32, device=X.device)
    loss = torch.empty((M,), dtype=torch.float32, device=X.device)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, BN),
    )
    
    linear_ce_fwd_kernel[grid](
        X, W, B, targets,
        max_buffer, sum_buffer, target_logits,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        BLOCK_N=BN
    )
    
    grid_red = (triton.cdiv(M, 128),)
    reduction_kernel[grid_red](
        max_buffer, sum_buffer, target_logits,
        loss,
        M, num_blocks_n,
        BLOCK_M=128
    )
    
    return loss
"""
        }
