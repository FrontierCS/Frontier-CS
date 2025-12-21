import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_forward_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    pid_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    pid_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = pid_m < M
    mask_n = pid_n < N
    
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_offs = k + tl.arange(0, BLOCK_SIZE_K)
        
        x_ptrs = X + pid_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
        w_ptrs = W + k_offs[:, None] * stride_wk + pid_n[None, :] * stride_wn
        
        x_mask = mask_m[:, None] & (k_offs[None, :] < K)
        w_mask = (k_offs[:, None] < K) & mask_n[None, :]
        
        x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float32)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
    
    if B is not None:
        b_ptrs = B + pid_n
        b = tl.load(b_ptrs, mask=mask_n, other=0.0).to(tl.float32)
        acc += b[None, :]
    
    # First pass: find row-wise maximum
    row_max = tl.max(acc, axis=1)
    
    # Compute exp(logits - max)
    exp_values = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_values, axis=1)
    
    # Load targets
    target_offs = pid_m
    target_mask = mask_m
    target_idx = tl.load(targets + target_offs, mask=target_mask, other=0)
    
    # Compute target logits using gather
    target_col_idx = target_idx[:, None]
    col_idx = pid_n[None, :]
    target_mask_gather = (col_idx == target_col_idx) & mask_m[:, None] & mask_n[None, :]
    
    target_logit = tl.sum(acc * target_mask_gather, axis=1)
    
    # Compute log-softmax: log(exp(logit - max) / sumexp) = logit - max - log(sumexp)
    log_softmax = target_logit - row_max - tl.log(row_sumexp)
    
    # Negative log likelihood
    nll = -log_softmax
    
    # Store output
    out_ptrs = output + pid_m * stride_om
    tl.store(out_ptrs, nll, mask=mask_m)

@triton.jit
def _fused_linear_ce_small_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid = tl.program_id(0)
    
    pid_m = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    mask_m = pid_m < M
    
    acc = tl.zeros((BLOCK_SIZE_M, N), dtype=tl.float32)
    
    # Process K dimension in blocks
    for k in range(0, K, BLOCK_SIZE_K):
        k_offs = k + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offs < K
        
        x_ptrs = X + pid_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
        w_ptrs = W + k_offs[:, None] * stride_wk + tl.arange(0, N)[None, :] * stride_wn
        
        x = tl.load(x_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & (tl.arange(0, N)[None, :] < N), other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
    
    if B is not None:
        b = tl.load(B + tl.arange(0, N), mask=(tl.arange(0, N) < N), other=0.0).to(tl.float32)
        acc += b[None, :]
    
    # First pass: find row-wise maximum
    row_max = tl.max(acc, axis=1)
    
    # Compute exp(logits - max)
    exp_values = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_values, axis=1)
    
    # Load targets
    target_idx = tl.load(targets + pid_m, mask=mask_m, other=0)
    
    # Gather target logits
    col_indices = tl.arange(0, N)[None, :]
    target_mask = (col_indices == target_idx[:, None]) & mask_m[:, None] & (col_indices < N)
    target_logit = tl.sum(acc * target_mask, axis=1)
    
    # Compute negative log likelihood
    nll = -target_logit + row_max + tl.log(row_sumexp)
    
    # Store output
    out_ptrs = output + pid_m * stride_om
    tl.store(out_ptrs, nll, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    """
    M, K = X.shape
    N = W.shape[1]
    
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    if M >= 128 and N >= 4096:
        grid = lambda meta: (
            triton.cdiv(M, meta['BLOCK_SIZE_M']),
            triton.cdiv(N, meta['BLOCK_SIZE_N']),
        )
        
        _fused_linear_ce_forward_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=128,
            BLOCK_SIZE_N=256,
            BLOCK_SIZE_K=64,
        )
    else:
        BLOCK_SIZE_M = 64 if M >= 64 else 32
        BLOCK_SIZE_K = 64
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M),)
        
        _fused_linear_ce_small_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_forward_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    pid_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    pid_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = pid_m < M
    mask_n = pid_n < N
    
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_offs = k + tl.arange(0, BLOCK_SIZE_K)
        
        x_ptrs = X + pid_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
        w_ptrs = W + k_offs[:, None] * stride_wk + pid_n[None, :] * stride_wn
        
        x_mask = mask_m[:, None] & (k_offs[None, :] < K)
        w_mask = (k_offs[:, None] < K) & mask_n[None, :]
        
        x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float32)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
    
    if B is not None:
        b_ptrs = B + pid_n
        b = tl.load(b_ptrs, mask=mask_n, other=0.0).to(tl.float32)
        acc += b[None, :]
    
    # First pass: find row-wise maximum
    row_max = tl.max(acc, axis=1)
    
    # Compute exp(logits - max)
    exp_values = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_values, axis=1)
    
    # Load targets
    target_offs = pid_m
    target_mask = mask_m
    target_idx = tl.load(targets + target_offs, mask=target_mask, other=0)
    
    # Compute target logits using gather
    target_col_idx = target_idx[:, None]
    col_idx = pid_n[None, :]
    target_mask_gather = (col_idx == target_col_idx) & mask_m[:, None] & mask_n[None, :]
    
    target_logit = tl.sum(acc * target_mask_gather, axis=1)
    
    # Compute log-softmax: log(exp(logit - max) / sumexp) = logit - max - log(sumexp)
    log_softmax = target_logit - row_max - tl.log(row_sumexp)
    
    # Negative log likelihood
    nll = -log_softmax
    
    # Store output
    out_ptrs = output + pid_m * stride_om
    tl.store(out_ptrs, nll, mask=mask_m)

@triton.jit
def _fused_linear_ce_small_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid = tl.program_id(0)
    
    pid_m = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    mask_m = pid_m < M
    
    acc = tl.zeros((BLOCK_SIZE_M, N), dtype=tl.float32)
    
    # Process K dimension in blocks
    for k in range(0, K, BLOCK_SIZE_K):
        k_offs = k + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offs < K
        
        x_ptrs = X + pid_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
        w_ptrs = W + k_offs[:, None] * stride_wk + tl.arange(0, N)[None, :] * stride_wn
        
        x = tl.load(x_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & (tl.arange(0, N)[None, :] < N), other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
    
    if B is not None:
        b = tl.load(B + tl.arange(0, N), mask=(tl.arange(0, N) < N), other=0.0).to(tl.float32)
        acc += b[None, :]
    
    # First pass: find row-wise maximum
    row_max = tl.max(acc, axis=1)
    
    # Compute exp(logits - max)
    exp_values = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_values, axis=1)
    
    # Load targets
    target_idx = tl.load(targets + pid_m, mask=mask_m, other=0)
    
    # Gather target logits
    col_indices = tl.arange(0, N)[None, :]
    target_mask = (col_indices == target_idx[:, None]) & mask_m[:, None] & (col_indices < N)
    target_logit = tl.sum(acc * target_mask, axis=1)
    
    # Compute negative log likelihood
    nll = -target_logit + row_max + tl.log(row_sumexp)
    
    # Store output
    out_ptrs = output + pid_m * stride_om
    tl.store(out_ptrs, nll, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    """
    M, K = X.shape
    N = W.shape[1]
    
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    if M >= 128 and N >= 4096:
        grid = lambda meta: (
            triton.cdiv(M, meta['BLOCK_SIZE_M']),
            triton.cdiv(N, meta['BLOCK_SIZE_N']),
        )
        
        _fused_linear_ce_forward_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=128,
            BLOCK_SIZE_N=256,
            BLOCK_SIZE_K=64,
        )
    else:
        BLOCK_SIZE_M = 64 if M >= 64 else 32
        BLOCK_SIZE_K = 64
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M),)
        
        _fused_linear_ce_small_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """''' + \
'''import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_forward_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    pid_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    pid_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    mask_m = pid_m < M
    mask_n = pid_n < N
    
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        k_offs = k + tl.arange(0, BLOCK_SIZE_K)
        
        x_ptrs = X + pid_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
        w_ptrs = W + k_offs[:, None] * stride_wk + pid_n[None, :] * stride_wn
        
        x_mask = mask_m[:, None] & (k_offs[None, :] < K)
        w_mask = (k_offs[:, None] < K) & mask_n[None, :]
        
        x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float32)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
    
    if B is not None:
        b_ptrs = B + pid_n
        b = tl.load(b_ptrs, mask=mask_n, other=0.0).to(tl.float32)
        acc += b[None, :]
    
    # First pass: find row-wise maximum
    row_max = tl.max(acc, axis=1)
    
    # Compute exp(logits - max)
    exp_values = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_values, axis=1)
    
    # Load targets
    target_offs = pid_m
    target_mask = mask_m
    target_idx = tl.load(targets + target_offs, mask=target_mask, other=0)
    
    # Compute target logits using gather
    target_col_idx = target_idx[:, None]
    col_idx = pid_n[None, :]
    target_mask_gather = (col_idx == target_col_idx) & mask_m[:, None] & mask_n[None, :]
    
    target_logit = tl.sum(acc * target_mask_gather, axis=1)
    
    # Compute log-softmax: log(exp(logit - max) / sumexp) = logit - max - log(sumexp)
    log_softmax = target_logit - row_max - tl.log(row_sumexp)
    
    # Negative log likelihood
    nll = -log_softmax
    
    # Store output
    out_ptrs = output + pid_m * stride_om
    tl.store(out_ptrs, nll, mask=mask_m)

@triton.jit
def _fused_linear_ce_small_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid = tl.program_id(0)
    
    pid_m = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    mask_m = pid_m < M
    
    acc = tl.zeros((BLOCK_SIZE_M, N), dtype=tl.float32)
    
    # Process K dimension in blocks
    for k in range(0, K, BLOCK_SIZE_K):
        k_offs = k + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offs < K
        
        x_ptrs = X + pid_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
        w_ptrs = W + k_offs[:, None] * stride_wk + tl.arange(0, N)[None, :] * stride_wn
        
        x = tl.load(x_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & (tl.arange(0, N)[None, :] < N), other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w)
    
    if B is not None:
        b = tl.load(B + tl.arange(0, N), mask=(tl.arange(0, N) < N), other=0.0).to(tl.float32)
        acc += b[None, :]
    
    # First pass: find row-wise maximum
    row_max = tl.max(acc, axis=1)
    
    # Compute exp(logits - max)
    exp_values = tl.exp(acc - row_max[:, None])
    row_sumexp = tl.sum(exp_values, axis=1)
    
    # Load targets
    target_idx = tl.load(targets + pid_m, mask=mask_m, other=0)
    
    # Gather target logits
    col_indices = tl.arange(0, N)[None, :]
    target_mask = (col_indices == target_idx[:, None]) & mask_m[:, None] & (col_indices < N)
    target_logit = tl.sum(acc * target_mask, axis=1)
    
    # Compute negative log likelihood
    nll = -target_logit + row_max + tl.log(row_sumexp)
    
    # Store output
    out_ptrs = output + pid_m * stride_om
    tl.store(out_ptrs, nll, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    """
    M, K = X.shape
    N = W.shape[1]
    
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    if M >= 128 and N >= 4096:
        grid = lambda meta: (
            triton.cdiv(M, meta['BLOCK_SIZE_M']),
            triton.cdiv(N, meta['BLOCK_SIZE_N']),
        )
        
        _fused_linear_ce_forward_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=128,
            BLOCK_SIZE_N=256,
            BLOCK_SIZE_K=64,
        )
    else:
        BLOCK_SIZE_M = 64 if M >= 64 else 32
        BLOCK_SIZE_K = 64
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M),)
        
        _fused_linear_ce_small_kernel[grid](
            X, W, B, targets, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
        )
    
    return output
'''}
        '''
        return {"code": code}
