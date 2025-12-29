import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_ce_phase1(
    X_ptr, W_ptr, B_ptr,
    max_ptr, sumexp_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    USE_FP16_ACC: tl.constexpr,
):
    pid = tl.program_id(0)
    pid_m = pid // tl.cdiv(N, BLOCK_N)
    pid_n = pid % tl.cdiv(N, BLOCK_N)
    
    m_off = pid_m * BLOCK_M
    n_off = pid_n * BLOCK_N
    
    m_mask = m_off + tl.arange(0, BLOCK_M) < M
    n_mask = n_off + tl.arange(0, BLOCK_N) < N
    
    # Initialize accumulator
    if USE_FP16_ACC:
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float16)
    else:
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    # Load bias block
    b_ptrs = B_ptr + (tl.arange(0, BLOCK_N) + n_off)
    bias = tl.load(b_ptrs, mask=n_mask, other=0.0)
    
    # Matrix multiplication with tiling
    for k_off in range(0, K, BLOCK_K):
        k_mask = k_off + tl.arange(0, BLOCK_K) < K
        
        # Load X block
        x_ptrs = X_ptr + (m_off[:, None] * stride_xm + 
                         (k_off + tl.arange(0, BLOCK_K)[None, :]) * stride_xk)
        x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
        
        # Load W block
        w_ptrs = W_ptr + ((k_off + tl.arange(0, BLOCK_K)[:, None]) * stride_wk + 
                         (n_off + tl.arange(0, BLOCK_N)[None, :]) * stride_wn)
        w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
        
        # Accumulate
        acc += tl.dot(x, w, allow_tf32=False)
    
    # Add bias
    acc += bias[None, :]
    
    # Convert to float32 for stable reduction
    acc_f32 = acc.to(tl.float32)
    
    # Find row-wise maximum
    if USE_FP16_ACC:
        row_max = tl.max(acc_f32, axis=1)
    else:
        row_max = tl.max(acc, axis=1)
    
    # Store max for each row
    max_ptrs = max_ptr + m_off + tl.arange(0, BLOCK_M)
    tl.store(max_ptrs, row_max, mask=m_mask)
    
    # Compute exp(acc - max) and sum
    row_max_expanded = tl.expand_dims(row_max, 1)
    exp_vals = tl.exp(acc_f32 - row_max_expanded)
    row_sumexp = tl.sum(exp_vals, axis=1)
    
    # Store sumexp for each row
    sumexp_ptrs = sumexp_ptr + m_off + tl.arange(0, BLOCK_M)
    tl.store(sumexp_ptrs, row_sumexp, mask=m_mask)


@triton.jit
def _fused_linear_ce_phase2(
    X_ptr, W_ptr, B_ptr, targets_ptr,
    max_ptr, sumexp_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    USE_FP16_ACC: tl.constexpr,
):
    pid_m = tl.program_id(0)
    m_off = pid_m * BLOCK_M
    m_mask = m_off + tl.arange(0, BLOCK_M) < M
    
    # Load targets for this block
    target_ptrs = targets_ptr + m_off + tl.arange(0, BLOCK_M)
    targets = tl.load(target_ptrs, mask=m_mask, other=0)
    
    # Load precomputed max and sumexp
    max_ptrs = max_ptr + m_off + tl.arange(0, BLOCK_M)
    sumexp_ptrs = sumexp_ptr + m_off + tl.arange(0, BLOCK_M)
    row_max = tl.load(max_ptrs, mask=m_mask, other=-float('inf'))
    row_sumexp = tl.load(sumexp_ptrs, mask=m_mask, other=0.0)
    
    # Initialize target logits
    target_logits = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process each target column
    for pid_n in range(tl.cdiv(N, BLOCK_N)):
        n_off = pid_n * BLOCK_N
        n_mask = n_off + tl.arange(0, BLOCK_N) < N
        
        # Check if this block contains any of our targets
        target_in_block = (targets >= n_off) & (targets < n_off + BLOCK_N)
        any_target = tl.any(target_in_block)
        
        if not any_target:
            continue
            
        # Initialize accumulator for this block
        if USE_FP16_ACC:
            acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float16)
        else:
            acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        
        # Load bias block
        b_ptrs = B_ptr + (tl.arange(0, BLOCK_N) + n_off)
        bias = tl.load(b_ptrs, mask=n_mask, other=0.0)
        
        # Matrix multiplication
        for k_off in range(0, K, BLOCK_K):
            k_mask = k_off + tl.arange(0, BLOCK_K) < K
            
            # Load X block
            x_ptrs = X_ptr + (m_off[:, None] * stride_xm + 
                             (k_off + tl.arange(0, BLOCK_K)[None, :]) * stride_xk)
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            
            # Load W block
            w_ptrs = W_ptr + ((k_off + tl.arange(0, BLOCK_K)[:, None]) * stride_wk + 
                             (n_off + tl.arange(0, BLOCK_N)[None, :]) * stride_wn)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            # Accumulate
            acc += tl.dot(x, w, allow_tf32=False)
        
        # Add bias and convert to float32
        acc += bias[None, :]
        acc_f32 = acc.to(tl.float32)
        
        # Extract target logits
        for i in range(BLOCK_M):
            if m_mask[i] and target_in_block[i]:
                col_idx = targets[i] - n_off
                if 0 <= col_idx < BLOCK_N:
                    target_logits = tl.where(
                        tl.arange(0, BLOCK_M) == i,
                        acc_f32[i, col_idx],
                        target_logits
                    )
    
    # Compute final loss: -log(exp(target_logit - max) / sumexp)
    # = max + log(sumexp) - target_logit
    log_sumexp = tl.log(row_sumexp)
    losses = row_max + log_sumexp - target_logits
    
    # Store results
    out_ptrs = output_ptr + m_off + tl.arange(0, BLOCK_M)
    tl.store(out_ptrs, losses, mask=m_mask)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    """
    M, K = X.shape
    N = W.shape[1]
    
    # Output tensor
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    # Intermediate tensors for two-pass algorithm
    max_vals = torch.empty(M, dtype=torch.float32, device=X.device)
    sumexp_vals = torch.empty(M, dtype=torch.float32, device=X.device)
    
    # Choose optimal block sizes based on problem dimensions
    # L4 GPU has 24GB VRAM, these sizes work well for K=4096, N=8192
    BLOCK_M = 128
    BLOCK_N = 256
    BLOCK_K = 64
    
    # Use fp16 accumulation for better performance on Ampere+
    USE_FP16_ACC = True
    
    # Phase 1: Compute row-wise max and sumexp
    grid1 = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)
    _fused_linear_ce_phase1[grid1](
        X, W, B,
        max_vals, sumexp_vals,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        USE_FP16_ACC=USE_FP16_ACC,
    )
    
    # Phase 2: Compute final losses using target indices
    grid2 = (triton.cdiv(M, BLOCK_M),)
    _fused_linear_ce_phase2[grid2](
        X, W, B, targets,
        max_vals, sumexp_vals, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        USE_FP16_ACC=USE_FP16_ACC,
    )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    @staticmethod
    def _get_code() -> str:
        import inspect
        return inspect.getsource(fused_linear_ce)