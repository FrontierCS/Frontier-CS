import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl

@triton.jit
def linear_ce_fwd_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr,
    Max_ptr, Sum_ptr, TVal_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_t,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    grid_n = tl.num_programs(1)

    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Load Bias (N,) - assume contiguous
    b_val = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)

    # Initialize accumulator (M, N) tile
    # Accumulate in float32 for precision
    accumulator = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32) + b_val[None, :]

    # Loop over K
    for k in range(0, K, BLOCK_K):
        # Load X tile: (BLOCK_M, BLOCK_K)
        # Check M bounds for rows, K bounds for cols
        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + (k + offs_k)[None, :] * stride_xk)
        x = tl.load(x_ptrs, mask=(offs_m[:, None] < M) & ((k + offs_k)[None, :] < K), other=0.0)

        # Load W tile: (BLOCK_K, BLOCK_N)
        w_ptrs = W_ptr + ((k + offs_k)[:, None] * stride_wk + offs_n[None, :] * stride_wn)
        w = tl.load(w_ptrs, mask=(offs_n[None, :] < N) & ((k + offs_k)[:, None] < K), other=0.0)

        # Matmul
        accumulator += tl.dot(x, w)

    # Apply mask for out-of-bounds columns (N)
    # This ensures they don't affect Max/Sum
    accumulator = tl.where(offs_n[None, :] < N, accumulator, float("-inf"))
    
    # 1. Local Max
    local_max = tl.max(accumulator, 1)

    # 2. Local Sum Exp
    diff = accumulator - local_max[:, None]
    exp_val = tl.exp(diff)
    local_sum = tl.sum(exp_val, 1)

    # 3. Target Extraction
    t_ptrs = T_ptr + offs_m * stride_t
    targets = tl.load(t_ptrs, mask=offs_m < M, other=-1)
    
    # Identify if targets are in this column block
    # offs_n is (BLOCK_N,), targets is (BLOCK_M,)
    # target_mask: (BLOCK_M, BLOCK_N)
    target_mask = (targets[:, None] == offs_n[None, :])
    
    # Sum out the target values (at most 1 per row will be non-zero across all blocks)
    # We use accumulator value directly
    target_val = tl.sum(accumulator * target_mask.to(tl.float32), 1)

    # Store partial results to global memory
    # Output shape: (M, grid_n)
    # Stride is implicitly (grid_n, 1) if we view as (M, grid_n)
    out_idx = offs_m[:, None] * grid_n + pid_n
    
    tl.store(Max_ptr + out_idx, local_max[:, None], mask=offs_m[:, None] < M)
    tl.store(Sum_ptr + out_idx, local_sum[:, None], mask=offs_m[:, None] < M)
    tl.store(TVal_ptr + out_idx, target_val[:, None], mask=offs_m[:, None] < M)

@triton.jit
def reduction_kernel(
    Max_ptr, Sum_ptr, TVal_ptr, Out_ptr,
    M, GRID_N,
    BLOCK_M: tl.constexpr
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    
    # Initialize globals
    global_max = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    
    # First pass: reduce max
    for i in range(GRID_N):
        idx = offs_m * GRID_N + i
        val = tl.load(Max_ptr + idx, mask=offs_m < M, other=float('-inf'))
        global_max = tl.maximum(global_max, val)
        
    # Second pass: reduce sum and target
    global_sum = tl.zeros([BLOCK_M], dtype=tl.float32)
    target_logit = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    for i in range(GRID_N):
        idx = offs_m * GRID_N + i
        m_val = tl.load(Max_ptr + idx, mask=offs_m < M, other=float('-inf'))
        s_val = tl.load(Sum_ptr + idx, mask=offs_m < M, other=0.0)
        t_val = tl.load(TVal_ptr + idx, mask=offs_m < M, other=0.0)
        
        # Adjust sum based on max difference
        global_sum += s_val * tl.exp(m_val - global_max)
        target_logit += t_val
        
    # Compute Final Loss
    # loss = log(sum(exp(x - m))) + m - x[target]
    loss = tl.log(global_sum) + global_max - target_logit
    
    tl.store(Out_ptr + offs_m, loss, mask=offs_m < M)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    
    # Block sizes
    # Optimized for L4 (Ada)
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_K = 64
    
    grid_n = (N + BLOCK_N - 1) // BLOCK_N
    grid_m = (M + BLOCK_M - 1) // BLOCK_M
    
    # Allocate intermediate buffers
    # Shape (M, grid_n)
    tmp_max = torch.empty((M, grid_n), device=X.device, dtype=torch.float32)
    tmp_sum = torch.empty((M, grid_n), device=X.device, dtype=torch.float32)
    tmp_tval = torch.empty((M, grid_n), device=X.device, dtype=torch.float32)
    
    # Phase 1: Compute partials
    linear_ce_fwd_kernel[(grid_m, grid_n)](
        X, W, B, targets,
        tmp_max, tmp_sum, tmp_tval,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        targets.stride(0),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8, num_stages=3
    )
    
    # Output buffer
    output = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Phase 2: Reduce
    reduction_kernel[(grid_m,)](
        tmp_max, tmp_sum, tmp_tval, output,
        M, grid_n,
        BLOCK_M=BLOCK_M,
        num_warps=4
    )
    
    return output
"""
        }
