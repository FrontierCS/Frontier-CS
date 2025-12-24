import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_forward_kernel(
    X, W, B,
    LOGITS,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_logits_m, stride_logits_n,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        accumulator += tl.dot(x, w)
        
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk
    
    offs_b = offs_n
    b = tl.load(B + offs_b * stride_bn, mask=offs_n < N, other=0.0)
    accumulator += b[None, :]
    
    offs_logits_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_logits_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    logits_ptrs = LOGITS + (offs_logits_m[:, None] * stride_logits_m + 
                           offs_logits_n[None, :] * stride_logits_n)
    
    mask = (offs_logits_m[:, None] < M) & (offs_logits_n[None, :] < N)
    tl.store(logits_ptrs, accumulator, mask=mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_first_pass_kernel(
    LOGITS,
    ROW_MAX,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_row_max,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    row_max = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    
    for n in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n_curr = n * BLOCK_SIZE_N + offs_n
        
        logits_ptrs = LOGITS + (offs_m[:, None] * stride_logits_m + 
                               offs_n_curr[None, :] * stride_logits_n)
        mask = (offs_m[:, None] < M) & (offs_n_curr[None, :] < N)
        
        logits_chunk = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
        row_max = tl.maximum(row_max, tl.max(logits_chunk, axis=1))
    
    row_max_ptrs = ROW_MAX + offs_m * stride_row_max
    tl.store(row_max_ptrs, row_max, mask=offs_m < M)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_second_pass_kernel(
    LOGITS, TARGETS, ROW_MAX,
    LOSS,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_row_max,
    stride_loss_m,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = offs_m < M
    
    row_max_ptrs = ROW_MAX + offs_m * stride_row_max
    row_max_vals = tl.load(row_max_ptrs, mask=mask_m, other=0.0)
    
    sum_exp = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    target_logits = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    for n in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n_curr = n * BLOCK_SIZE_N + offs_n
        
        logits_ptrs = LOGITS + (offs_m[:, None] * stride_logits_m + 
                               offs_n_curr[None, :] * stride_logits_n)
        mask = mask_m[:, None] & (offs_n_curr[None, :] < N)
        
        logits_chunk = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
        stable_logits = logits_chunk - row_max_vals[:, None]
        
        exp_vals = tl.exp(stable_logits)
        sum_exp += tl.sum(exp_vals, axis=1)
        
        if n == 0:
            target_ptrs = TARGETS + offs_m * stride_targets_m
            target_indices = tl.load(target_ptrs, mask=mask_m, other=0)
        
        target_mask = (offs_n_curr[None, :] == target_indices[:, None]) & mask
        target_logits += tl.sum(logits_chunk * target_mask, axis=1)
    
    log_sum_exp = tl.log(sum_exp) + row_max_vals
    loss_vals = log_sum_exp - target_logits
    
    loss_ptrs = LOSS + offs_m * stride_loss_m
    tl.store(loss_ptrs, loss_vals, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    
    device = X.device
    
    LOGITS = torch.empty((M, N), device=device, dtype=torch.float32)
    ROW_MAX = torch.empty((M,), device=device, dtype=torch.float32)
    LOSS = torch.empty((M,), device=device, dtype=torch.float32)
    
    grid_linear = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
        triton.cdiv(N, META['BLOCK_SIZE_N']),
    )
    
    _linear_forward_kernel[grid_linear](
        X, W, B,
        LOGITS,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        LOGITS.stride(0), LOGITS.stride(1),
    )
    
    grid_first_pass = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
    )
    
    _cross_entropy_first_pass_kernel[grid_first_pass](
        LOGITS,
        ROW_MAX,
        M, N,
        LOGITS.stride(0), LOGITS.stride(1),
        ROW_MAX.stride(0),
    )
    
    grid_second_pass = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
    )
    
    _cross_entropy_second_pass_kernel[grid_second_pass](
        LOGITS, targets, ROW_MAX,
        LOSS,
        M, N,
        LOGITS.stride(0), LOGITS.stride(1),
        targets.stride(0),
        ROW_MAX.stride(0),
        LOSS.stride(0),
    )
    
    return LOSS

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_forward_kernel(
    X, W, B,
    LOGITS,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_logits_m, stride_logits_n,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_SIZE_K)
        mask_w = (offs_k[:, None] < K - k * BLOCK_SIZE_K) & (offs_n[None, :] < N)
        
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        accumulator += tl.dot(x, w)
        
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk
    
    offs_b = offs_n
    b = tl.load(B + offs_b * stride_bn, mask=offs_n < N, other=0.0)
    accumulator += b[None, :]
    
    offs_logits_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_logits_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    logits_ptrs = LOGITS + (offs_logits_m[:, None] * stride_logits_m + 
                           offs_logits_n[None, :] * stride_logits_n)
    
    mask = (offs_logits_m[:, None] < M) & (offs_logits_n[None, :] < N)
    tl.store(logits_ptrs, accumulator, mask=mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_first_pass_kernel(
    LOGITS,
    ROW_MAX,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_row_max,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    row_max = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    
    for n in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n_curr = n * BLOCK_SIZE_N + offs_n
        
        logits_ptrs = LOGITS + (offs_m[:, None] * stride_logits_m + 
                               offs_n_curr[None, :] * stride_logits_n)
        mask = (offs_m[:, None] < M) & (offs_n_curr[None, :] < N)
        
        logits_chunk = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
        row_max = tl.maximum(row_max, tl.max(logits_chunk, axis=1))
    
    row_max_ptrs = ROW_MAX + offs_m * stride_row_max
    tl.store(row_max_ptrs, row_max, mask=offs_m < M)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_second_pass_kernel(
    LOGITS, TARGETS, ROW_MAX,
    LOSS,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_row_max,
    stride_loss_m,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = offs_m < M
    
    row_max_ptrs = ROW_MAX + offs_m * stride_row_max
    row_max_vals = tl.load(row_max_ptrs, mask=mask_m, other=0.0)
    
    sum_exp = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    target_logits = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    for n in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n_curr = n * BLOCK_SIZE_N + offs_n
        
        logits_ptrs = LOGITS + (offs_m[:, None] * stride_logits_m + 
                               offs_n_curr[None, :] * stride_logits_n)
        mask = mask_m[:, None] & (offs_n_curr[None, :] < N)
        
        logits_chunk = tl.load(logits_ptrs, mask=mask, other=float('-inf'))
        stable_logits = logits_chunk - row_max_vals[:, None]
        
        exp_vals = tl.exp(stable_logits)
        sum_exp += tl.sum(exp_vals, axis=1)
        
        if n == 0:
            target_ptrs = TARGETS + offs_m * stride_targets_m
            target_indices = tl.load(target_ptrs, mask=mask_m, other=0)
        
        target_mask = (offs_n_curr[None, :] == target_indices[:, None]) & mask
        target_logits += tl.sum(logits_chunk * target_mask, axis=1)
    
    log_sum_exp = tl.log(sum_exp) + row_max_vals
    loss_vals = log_sum_exp - target_logits
    
    loss_ptrs = LOSS + offs_m * stride_loss_m
    tl.store(loss_ptrs, loss_vals, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    
    device = X.device
    
    LOGITS = torch.empty((M, N), device=device, dtype=torch.float32)
    ROW_MAX = torch.empty((M,), device=device, dtype=torch.float32)
    LOSS = torch.empty((M,), device=device, dtype=torch.float32)
    
    grid_linear = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
        triton.cdiv(N, META['BLOCK_SIZE_N']),
    )
    
    _linear_forward_kernel[grid_linear](
        X, W, B,
        LOGITS,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        LOGITS.stride(0), LOGITS.stride(1),
    )
    
    grid_first_pass = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
    )
    
    _cross_entropy_first_pass_kernel[grid_first_pass](
        LOGITS,
        ROW_MAX,
        M, N,
        LOGITS.stride(0), LOGITS.stride(1),
        ROW_MAX.stride(0),
    )
    
    grid_second_pass = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']),
    )
    
    _cross_entropy_second_pass_kernel[grid_second_pass](
        LOGITS, targets, ROW_MAX,
        LOSS,
        M, N,
        LOGITS.stride(0), LOGITS.stride(1),
        targets.stride(0),
        ROW_MAX.stride(0),
        LOSS.stride(0),
    )
    
    return LOSS
'''
        return {"code": code}
