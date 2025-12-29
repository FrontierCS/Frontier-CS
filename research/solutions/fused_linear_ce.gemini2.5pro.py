import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, Loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_loss_m,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    """
    Triton kernel for fused linear layer and cross-entropy loss.
    This kernel uses a single-program, two-pass approach to compute the loss
    for a block of rows, avoiding intermediate writes to global memory.
    """
    pid = tl.program_id(0)
    m_offs = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    m_mask = m_offs < M

    # Pass 1: Find the row-wise maximum of logits for numerical stability.
    # This is the 'max' term in the log-sum-exp trick.
    row_max = tl.full([BLOCK_SIZE_M], value=-float('inf'), dtype=tl.float32)
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offs = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offs < N
        
        # Compute a block of logits: acc = X @ W
        acc = tl.zeros([BLOCK_SIZE_M, BLOCK_SIZE_N], dtype=tl.float32)
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offs = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offs < K
            
            x_ptrs = X_ptr + (m_offs[:, None] * stride_xm + k_offs[None, :] * stride_xk)
            w_ptrs = W_ptr + (k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn)
            
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x, w)

        # Add bias: logits = acc + B
        b_ptrs = B_ptr + n_offs
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b[None, :]
        
        # Mask out-of-bounds logits before reduction to prevent them from affecting the max
        logits_masked = tl.where(n_mask[None, :], logits, -float('inf'))
        current_max = tl.max(logits_masked, axis=1)
        row_max = tl.maximum(row_max, current_max)

    # Pass 2: Re-compute logits to calculate sum_exp and gather the target logit.
    # This avoids storing the entire (M, N) logit matrix.
    sum_exp = tl.zeros([BLOCK_SIZE_M], dtype=tl.float32)
    target_logit = tl.zeros([BLOCK_SIZE_M], dtype=tl.float32)
    
    target_idx = tl.load(targets_ptr + m_offs, mask=m_mask)

    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offs = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offs < N

        # Recompute the block of logits
        acc = tl.zeros([BLOCK_SIZE_M, BLOCK_SIZE_N], dtype=tl.float32)
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offs = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offs < K

            x_ptrs = X_ptr + (m_offs[:, None] * stride_xm + k_offs[None, :] * stride_xk)
            w_ptrs = W_ptr + (k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn)
            
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x, w)
        
        b_ptrs = B_ptr + n_offs
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b[None, :]
        
        # Compute sum(exp(logits - max))
        logits_minus_max = logits - row_max[:, None]
        exp_logits = tl.exp(logits_minus_max)
        sum_exp += tl.sum(tl.where(m_mask[:, None] & n_mask[None, :], exp_logits, 0.0), axis=1)
        
        # Gather the logit corresponding to the target index
        target_mask = (target_idx[:, None] == n_offs[None, :])
        # tl.sum with a one-hot mask acts as a gather operation
        target_logit_from_block = tl.sum(logits * target_mask.to(logits.dtype), axis=1)
        target_logit += target_logit_from_block

    # Final loss calculation using the log-sum-exp formula:
    # NLL = -log(softmax(logits)[target])
    #     = - (target_logit - log(sum(exp(logits))))
    #     = log(sum(exp(logits))) - target_logit
    #     = max + log(sum(exp(logits - max))) - target_logit
    loss = row_max + tl.log(sum_exp) - target_logit

    loss_ptrs = Loss_ptr + m_offs * stride_loss_m
    tl.store(loss_ptrs, loss, mask=m_mask)


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
    _K, N = W.shape
    assert K == _K, f"Shape mismatch: X({X.shape}) @ W({W.shape})"
    assert B.shape == (N,), f"Shape mismatch: B({B.shape}) vs N={N}"
    assert targets.shape == (M,), f"Shape mismatch: targets({targets.shape}) vs M={M}"

    output = torch.empty(M, device=X.device, dtype=torch.float32)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']),)
    
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0),
    )
    
    return output


_solution_code = '''
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=5, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, Loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_loss_m,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    """
    Triton kernel for fused linear layer and cross-entropy loss.
    This kernel uses a single-program, two-pass approach to compute the loss
    for a block of rows, avoiding intermediate writes to global memory.
    """
    pid = tl.program_id(0)
    m_offs = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    m_mask = m_offs < M

    # Pass 1: Find the row-wise maximum of logits for numerical stability.
    # This is the 'max' term in the log-sum-exp trick.
    row_max = tl.full([BLOCK_SIZE_M], value=-float('inf'), dtype=tl.float32)
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offs = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offs < N
        
        # Compute a block of logits: acc = X @ W
        acc = tl.zeros([BLOCK_SIZE_M, BLOCK_SIZE_N], dtype=tl.float32)
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offs = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offs < K
            
            x_ptrs = X_ptr + (m_offs[:, None] * stride_xm + k_offs[None, :] * stride_xk)
            w_ptrs = W_ptr + (k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn)
            
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x, w)

        # Add bias: logits = acc + B
        b_ptrs = B_ptr + n_offs
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b[None, :]
        
        # Mask out-of-bounds logits before reduction to prevent them from affecting the max
        logits_masked = tl.where(n_mask[None, :], logits, -float('inf'))
        current_max = tl.max(logits_masked, axis=1)
        row_max = tl.maximum(row_max, current_max)

    # Pass 2: Re-compute logits to calculate sum_exp and gather the target logit.
    # This avoids storing the entire (M, N) logit matrix.
    sum_exp = tl.zeros([BLOCK_SIZE_M], dtype=tl.float32)
    target_logit = tl.zeros([BLOCK_SIZE_M], dtype=tl.float32)
    
    target_idx = tl.load(targets_ptr + m_offs, mask=m_mask)

    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offs = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offs < N

        # Recompute the block of logits
        acc = tl.zeros([BLOCK_SIZE_M, BLOCK_SIZE_N], dtype=tl.float32)
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offs = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offs < K

            x_ptrs = X_ptr + (m_offs[:, None] * stride_xm + k_offs[None, :] * stride_xk)
            w_ptrs = W_ptr + (k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn)
            
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x, w)
        
        b_ptrs = B_ptr + n_offs
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b[None, :]
        
        # Compute sum(exp(logits - max))
        logits_minus_max = logits - row_max[:, None]
        exp_logits = tl.exp(logits_minus_max)
        sum_exp += tl.sum(tl.where(m_mask[:, None] & n_mask[None, :], exp_logits, 0.0), axis=1)
        
        # Gather the logit corresponding to the target index
        target_mask = (target_idx[:, None] == n_offs[None, :])
        # tl.sum with a one-hot mask acts as a gather operation
        target_logit_from_block = tl.sum(logits * target_mask.to(logits.dtype), axis=1)
        target_logit += target_logit_from_block

    # Final loss calculation using the log-sum-exp formula:
    # NLL = -log(softmax(logits)[target])
    #     = - (target_logit - log(sum(exp(logits))))
    #     = log(sum(exp(logits))) - target_logit
    #     = max + log(sum(exp(logits - max))) - target_logit
    loss = row_max + tl.log(sum_exp) - target_logit

    loss_ptrs = Loss_ptr + m_offs * stride_loss_m
    tl.store(loss_ptrs, loss, mask=m_mask)


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
    _K, N = W.shape
    assert K == _K, f"Shape mismatch: X({X.shape}) @ W({W.shape})"
    assert B.shape == (N,), f"Shape mismatch: B({B.shape}) vs N={N}"
    assert targets.shape == (M,), f"Shape mismatch: targets({targets.shape}) vs M={M}"

    output = torch.empty(M, device=X.device, dtype=torch.float32)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']),)
    
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0),
    )
    
    return output
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _solution_code}