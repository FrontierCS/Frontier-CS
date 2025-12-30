import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K']
)
@triton.jit
def _fused_linear_ce_forward_kernel(
    X, W, B, T, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_tm,
    stride_lm,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = min(K - k, BLOCK_K)
        x = tl.load(x_ptrs, mask=offs_k[None, :] < k_remaining, other=0.0)
        w = tl.load(w_ptrs, mask=offs_k[:, None] < k_remaining, other=0.0)
        acc += tl.dot(x, w)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    b_ptrs = B + offs_n
    b = tl.load(b_ptrs)
    acc += b[None, :]
    
    row_max = tl.max(acc, axis=1)
    exp_vals = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_vals, axis=1)
    
    t_ptrs = T + offs_m
    t = tl.load(t_ptrs)
    
    target_mask = (t[:, None] >= offs_n[None, :]) & (t[:, None] < offs_n[None, :] + BLOCK_N)
    target_logits = tl.sum(acc * target_mask, axis=1)
    
    row_loss = -target_logits + row_max + tl.log(row_sumexp)
    
    l_ptrs = L + offs_m * stride_lm
    tl.store(l_ptrs, row_loss, mask=offs_m < M)

@triton.jit
def _fused_linear_ce_forward_kernel_fast(
    X, W, B, T, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_tm,
    stride_lm,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        x = tl.load(x_ptrs)
        w = tl.load(w_ptrs)
        acc += tl.dot(x, w)
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    b_ptrs = B + offs_n
    b = tl.load(b_ptrs)
    acc += b[None, :]
    
    if pid_n == 0:
        row_max = tl.max(acc, axis=1)
        row_sumexp = tl.sum(tl.exp(acc - row_max[:, None]), axis=1)
        
        t_ptrs = T + offs_m
        t = tl.load(t_ptrs)
        
        target_mask = (t[:, None] >= offs_n[None, :]) & (t[:, None] < offs_n[None, :] + BLOCK_N)
        target_logits = tl.sum(acc * target_mask, axis=1)
        
        loss = tl.where(offs_m < M, 
                       -target_logits + row_max + tl.log(row_sumexp),
                       0.0)
        
        l_ptrs = L + offs_m * stride_lm
        tl.store(l_ptrs, loss)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    L = torch.empty(M, dtype=torch.float32, device=X.device)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    
    if M <= 512 and K <= 4096 and N <= 8192:
        _fused_linear_ce_forward_kernel_fast[grid](
            X, W, B, targets, L,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            targets.stride(0),
            L.stride(0),
            BLOCK_M=64, BLOCK_N=256, BLOCK_K=64
        )
    else:
        _fused_linear_ce_forward_kernel[grid](
            X, W, B, targets, L,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            targets.stride(0),
            L.stride(0)
        )
    
    return L

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K']
)
@triton.jit
def _fused_linear_ce_forward_kernel(
    X, W, B, T, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_tm,
    stride_lm,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = min(K - k, BLOCK_K)
        x = tl.load(x_ptrs, mask=offs_k[None, :] < k_remaining, other=0.0)
        w = tl.load(w_ptrs, mask=offs_k[:, None] < k_remaining, other=0.0)
        acc += tl.dot(x, w)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    b_ptrs = B + offs_n
    b = tl.load(b_ptrs)
    acc += b[None, :]
    
    row_max = tl.max(acc, axis=1)
    exp_vals = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_vals, axis=1)
    
    t_ptrs = T + offs_m
    t = tl.load(t_ptrs)
    
    target_mask = (t[:, None] >= offs_n[None, :]) & (t[:, None] < offs_n[None, :] + BLOCK_N)
    target_logits = tl.sum(acc * target_mask, axis=1)
    
    row_loss = -target_logits + row_max + tl.log(row_sumexp)
    
    l_ptrs = L + offs_m * stride_lm
    tl.store(l_ptrs, row_loss, mask=offs_m < M)

@triton.jit
def _fused_linear_ce_forward_kernel_fast(
    X, W, B, T, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_tm,
    stride_lm,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    x_ptrs = X + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    w_ptrs = W + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        x = tl.load(x_ptrs)
        w = tl.load(w_ptrs)
        acc += tl.dot(x, w)
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    b_ptrs = B + offs_n
    b = tl.load(b_ptrs)
    acc += b[None, :]
    
    if pid_n == 0:
        row_max = tl.max(acc, axis=1)
        row_sumexp = tl.sum(tl.exp(acc - row_max[:, None]), axis=1)
        
        t_ptrs = T + offs_m
        t = tl.load(t_ptrs)
        
        target_mask = (t[:, None] >= offs_n[None, :]) & (t[:, None] < offs_n[None, :] + BLOCK_N)
        target_logits = tl.sum(acc * target_mask, axis=1)
        
        loss = tl.where(offs_m < M, 
                       -target_logits + row_max + tl.log(row_sumexp),
                       0.0)
        
        l_ptrs = L + offs_m * stride_lm
        tl.store(l_ptrs, loss)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    L = torch.empty(M, dtype=torch.float32, device=X.device)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
    )
    
    if M <= 512 and K <= 4096 and N <= 8192:
        _fused_linear_ce_forward_kernel_fast[grid](
            X, W, B, targets, L,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            targets.stride(0),
            L.stride(0),
            BLOCK_M=64, BLOCK_N=256, BLOCK_K=64
        )
    else:
        _fused_linear_ce_forward_kernel[grid](
            X, W, B, targets, L,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            targets.stride(0),
            L.stride(0)
        )
    
    return L
'''
        return {"code": code}