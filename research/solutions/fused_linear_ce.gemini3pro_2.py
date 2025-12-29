import torch
import triton
import triton.language as tl
import inspect
import sys

@triton.jit
def linear_ce_fwd_kernel_stage1(
    X_ptr, W_ptr, B_ptr, T_ptr,
    Max_ptr, Sum_ptr, TLogit_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_max_m, stride_max_n,
    stride_sum_m, stride_sum_n,
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
    
    # Initialize pointers
    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_offs = k * BLOCK_K + offs_k
        
        # Load X and W with boundary checks
        x = tl.load(x_ptrs, mask=(offs_m[:, None] < M) & (k_offs[None, :] < K), other=0.0)
        w = tl.load(w_ptrs, mask=(k_offs[:, None] < K) & (offs_n[None, :] < N), other=0.0)
        
        accumulator += tl.dot(x, w)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
        
    # Add Bias
    b_ptrs = B_ptr + offs_n
    bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
    accumulator += bias[None, :]
    
    # Mask out-of-bounds N cols with -inf for max calculation
    accumulator = tl.where(offs_n[None, :] < N, accumulator, float("-inf"))
    
    # Compute local max and sum_exp
    local_max = tl.max(accumulator, 1)
    local_exp = tl.exp(accumulator - local_max[:, None])
    # Mask again for sum to ensure padding doesn't contribute
    local_sum = tl.sum(tl.where(offs_n[None, :] < N, local_exp, 0.0), 1)
    
    # Store partial stats
    out_m_offs = offs_m
    out_n_idx = pid_n
    
    max_out_ptrs = Max_ptr + (out_m_offs * stride_max_m + out_n_idx * stride_max_n)
    sum_out_ptrs = Sum_ptr + (out_m_offs * stride_sum_m + out_n_idx * stride_sum_n)
    
    tl.store(max_out_ptrs, local_max, mask=out_m_offs < M)
    tl.store(sum_out_ptrs, local_sum, mask=out_m_offs < M)
    
    # Extract Target Logit
    targets = tl.load(T_ptr + offs_m, mask=offs_m < M, other=-1)
    
    # Check which rows have their target in this column block
    n_start = pid_n * BLOCK_N
    
    # Only calculate if necessary
    match_mask = targets[:, None] == offs_n[None, :]
    val = tl.sum(tl.where(match_mask, accumulator, 0.0), 1)
    
    found_mask = (targets >= n_start) & (targets < n_start + BLOCK_N) & (offs_m < M)
    tlogit_ptrs = TLogit_ptr + offs_m
    tl.store(tlogit_ptrs, val, mask=found_mask)

@triton.jit
def linear_ce_loss_kernel(
    Max_ptr, Sum_ptr, TLogit_ptr, Out_ptr,
    M, N_GRID,
    stride_max_m, stride_max_n,
    stride_sum_m, stride_sum_n,
    BLOCK_M: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    # Initialize global stats
    global_max = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    global_sum = tl.full([BLOCK_M], 0.0, dtype=tl.float32)
    
    # Reduce across N_GRID
    for i in range(N_GRID):
        p_max_ptr = Max_ptr + offs_m * stride_max_m + i * stride_max_n
        p_sum_ptr = Sum_ptr + offs_m * stride_sum_m + i * stride_sum_n
        
        curr_max = tl.load(p_max_ptr, mask=mask_m, other=float("-inf"))
        curr_sum = tl.load(p_sum_ptr, mask=mask_m, other=0.0)
        
        # Online softmax reduction
        new_max = tl.maximum(global_max, curr_max)
        
        # Scale factor handling for -inf
        term1 = global_sum * tl.exp(global_max - new_max)
        term2 = curr_sum * tl.exp(curr_max - new_max)
        
        global_max = new_max
        global_sum = term1 + term2
        
    t_logit = tl.load(TLogit_ptr + offs_m, mask=mask_m, other=0.0)
    
    # Loss = log(sum_exp) + max - target_logit
    loss = tl.log(global_sum) + global_max - t_logit
    
    tl.store(Out_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    """
    M, K = X.shape
    K2, N = W.shape
    assert K == K2, "Dimension mismatch between X and W"
    
    losses = torch.empty(M, device=X.device, dtype=torch.float32)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_K = 64
    GROUP_SIZE_M = 8
    
    grid_n = triton.cdiv(N, BLOCK_N)
    
    # Intermediate buffers for split-N reduction
    mid_max = torch.empty((M, grid_n), device=X.device, dtype=torch.float32)
    mid_sum = torch.empty((M, grid_n), device=X.device, dtype=torch.float32)
    mid_tlogits = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Stage 1: Matmul + Partial Stats
    grid1 = (triton.cdiv(M, BLOCK_M) * grid_n, )
    linear_ce_fwd_kernel_stage1[grid1](
        X, W, B, targets,
        mid_max, mid_sum, mid_tlogits,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        mid_max.stride(0), mid_max.stride(1),
        mid_sum.stride(0), mid_sum.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_SIZE_M=GROUP_SIZE_M,
        num_warps=4, num_stages=3
    )
    
    # Stage 2: Reduction
    grid2 = (triton.cdiv(M, BLOCK_M), )
    linear_ce_loss_kernel[grid2](
        mid_max, mid_sum, mid_tlogits, losses,
        M, grid_n,
        mid_max.stride(0), mid_max.stride(1),
        mid_sum.stride(0), mid_sum.stride(1),
        BLOCK_M=BLOCK_M,
        num_warps=4
    )
    
    return losses

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": inspect.getsource(sys.modules[__name__])}