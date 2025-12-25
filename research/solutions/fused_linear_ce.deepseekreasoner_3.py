import torch
import triton
import triton.language as tl
from typing import Optional, Tuple


@triton.jit
def fused_linear_ce_kernel(
    # Pointers to matrices
    x_ptr, w_ptr, b_ptr, targets_ptr, output_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides for X
    stride_xm, stride_xk,
    # Strides for W
    stride_wk, stride_wn,
    # Strides for output
    stride_out_m,
    # Block sizes
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_M: tl.constexpr = 8,
    # Compute type
    ACCUM_DTYPE: tl.constexpr = tl.float32,
):
    """
    Fused linear layer with cross entropy loss kernel.
    Implements two-pass algorithm for numerical stability.
    """
    # Program ID
    pid = tl.program_id(axis=0)
    
    # Number of programs along M dimension
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # Offsets for X [BLOCK_M, BLOCK_K]
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_k = tl.arange(0, BLOCK_K)
    
    # Offsets for W [BLOCK_K, BLOCK_N]
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Initialize pointers to X
    x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    
    # Initialize pointers to W
    w_ptrs = w_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    # Accumulator for first pass (max values)
    acc_max = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    
    # Load bias for this block
    b_ptrs = b_ptr + offs_n
    bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0).to(ACCUM_DTYPE)
    
    # Initialize accumulator for logits
    acc_logits = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    
    # Compute logits block by block
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Load block of X
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_K)
        x = tl.load(x_ptrs, mask=mask_x, other=0.0).to(ACCUM_DTYPE)
        
        # Load block of W
        mask_w = (offs_k[:, None] < K - k * BLOCK_K) & (offs_n[None, :] < N)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0).to(ACCUM_DTYPE)
        
        # Matrix multiplication
        acc_logits += tl.dot(x, w)
        
        # Update pointers
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    # Add bias
    acc_logits += bias[None, :]
    
    # Find row-wise max in this block
    row_max = tl.max(acc_logits, axis=1)
    
    # Store intermediate max for reduction
    # We'll use shared memory for final reduction
    max_ptr = output_ptr + pid * BLOCK_M * 2  # Temporary storage
    tl.store(max_ptr + offs_m, row_max, mask=offs_m < M)


@triton.jit
def fused_linear_ce_reduce_kernel(
    # Pointers
    x_ptr, w_ptr, b_ptr, targets_ptr, output_ptr,
    # Intermediate storage
    temp_max_ptr, temp_sumexp_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_out_m,
    # Block sizes
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_M: tl.constexpr = 8,
    # Compute type
    ACCUM_DTYPE: tl.constexpr = tl.float32,
):
    """
    Second pass: compute sumexp and gather target logits
    """
    pid = tl.program_id(axis=0)
    
    # Similar program ID logic as first kernel
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # Offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_k = tl.arange(0, BLOCK_K)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Initialize pointers
    x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = w_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
    
    # Load bias
    b_ptrs = b_ptr + offs_n
    bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0).to(ACCUM_DTYPE)
    
    # Compute logits again (could be optimized to store from first pass)
    acc_logits = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACCUM_DTYPE)
    
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K - k * BLOCK_K)
        x = tl.load(x_ptrs, mask=mask_x, other=0.0).to(ACCUM_DTYPE)
        
        mask_w = (offs_k[:, None] < K - k * BLOCK_K) & (offs_n[None, :] < N)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0).to(ACCUM_DTYPE)
        
        acc_logits += tl.dot(x, w)
        
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk
    
    acc_logits += bias[None, :]
    
    # Load row max from first pass
    row_max = tl.load(temp_max_ptr + offs_m, mask=offs_m < M, other=-float('inf'))
    
    # Compute exp(logits - row_max) for numerical stability
    exp_logits = tl.exp(acc_logits - row_max[:, None])
    
    # Compute sumexp for this block
    row_sumexp = tl.sum(exp_logits, axis=1)
    
    # Store sumexp for reduction
    tl.store(temp_sumexp_ptr + pid * BLOCK_M + offs_m, row_sumexp, mask=offs_m < M)
    
    # Gather target logits if target is in this block
    # Load targets for this block
    targets = tl.load(targets_ptr + offs_m, mask=offs_m < M, other=0)
    
    # Check if target is in current column block
    target_mask = (targets[:, None] >= offs_n[None, :]) & \
                  (targets[:, None] < offs_n[None, :] + BLOCK_N)
    
    # Extract target logits
    target_logits = tl.sum(acc_logits * target_mask, axis=1)
    
    # Store target logits for final computation
    tl.store(temp_max_ptr + pid * BLOCK_M + offs_m, target_logits, mask=offs_m < M)


@triton.jit
def fused_linear_ce_final_kernel(
    # Pointers
    output_ptr,
    temp_max_ptr,  # Now stores target logits
    temp_sumexp_ptr,
    # Dimensions
    M, N,
    stride_out_m,
    # Block size
    BLOCK_M: tl.constexpr,
):
    """
    Final kernel: compute loss from row_max, sumexp, and target logits
    """
    pid = tl.program_id(axis=0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    
    # Load target logits
    target_logits = tl.load(temp_max_ptr + offs_m, mask=offs_m < M, other=0.0)
    
    # Load sumexp (already reduced)
    sumexp = tl.load(temp_sumexp_ptr + offs_m, mask=offs_m < M, other=1.0)
    
    # Compute log sumexp
    log_sumexp = tl.log(sumexp)
    
    # Compute loss: -target_logit + log_sumexp
    # Note: row_max is already accounted for in sumexp calculation
    loss = -target_logits + log_sumexp
    
    # Store final loss
    tl.store(output_ptr + offs_m * stride_out_m, loss, mask=offs_m < M)


@triton.jit
def fused_linear_ce_single_kernel(
    # Pointers to matrices
    x_ptr, w_ptr, b_ptr, targets_ptr, output_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides for X
    stride_xm, stride_xk,
    # Strides for W
    stride_wk, stride_wn,
    # Strides for output
    stride_out_m,
    # Block sizes
    BLOCK_M: tl.constexpr,
    BLOCK_K: tl.constexpr,
    BLOCK_N: tl.constexpr,
    # Compute type
    ACCUM_DTYPE: tl.constexpr = tl.float32,
):
    """
    Single kernel implementation for smaller problems
    """
    pid = tl.program_id(axis=0)
    
    # Each program handles one row
    row_idx = pid
    
    if row_idx >= M:
        return
    
    # Load target for this row
    target_idx = tl.load(targets_ptr + row_idx)
    
    # Initialize accumulators
    row_max = tl.full([1], -float('inf'), dtype=ACCUM_DTYPE)
    sumexp = tl.zeros([1], dtype=ACCUM_DTYPE)
    target_logit = tl.zeros([1], dtype=ACCUM_DTYPE)
    
    # Process columns in blocks
    for col_block in range(0, N, BLOCK_N):
        col_offs = col_block + tl.arange(0, BLOCK_N)
        col_mask = col_offs < N
        
        # Initialize accumulator for this column block
        acc = tl.zeros([BLOCK_N], dtype=ACCUM_DTYPE)
        
        # Compute linear layer for this column block
        for k_block in range(0, K, BLOCK_K):
            k_offs = k_block + tl.arange(0, BLOCK_K)
            k_mask = k_offs < K
            
            # Load X element
            x_offset = row_idx * stride_xm + k_offs * stride_xk
            x = tl.load(x_ptr + x_offset, mask=k_mask, other=0.0).to(ACCUM_DTYPE)
            
            # Load W block
            w_ptrs = w_ptr + k_offs[:, None] * stride_wk + col_offs[None, :] * stride_wn
            w = tl.load(w_ptrs, mask=k_mask[:, None] & col_mask[None, :], other=0.0).to(ACCUM_DTYPE)
            
            # Accumulate
            acc += tl.sum(x[:, None] * w, axis=0)
        
        # Add bias
        b = tl.load(b_ptr + col_offs, mask=col_mask, other=0.0).to(ACCUM_DTYPE)
        acc += b
        
        # Update row max
        block_max = tl.max(acc, where=col_mask, initial=-float('inf'))
        row_max = tl.maximum(row_max, block_max)
        
        # Store for second pass
        # We'll compute exp in place
        
        # Check if target is in this block
        target_in_block = (target_idx >= col_block) & (target_idx < col_block + BLOCK_N)
        if target_in_block:
            target_offset = target_idx - col_block
            target_logit = tl.where(target_offset < BLOCK_N, acc[target_offset], target_logit)
    
    # Reset sumexp for second pass
    sumexp = tl.zeros([1], dtype=ACCUM_DTYPE)
    
    # Second pass: compute sumexp with stable computation
    for col_block in range(0, N, BLOCK_N):
        col_offs = col_block + tl.arange(0, BLOCK_N)
        col_mask = col_offs < N
        
        # Recompute or store from first pass? Let's recompute for simplicity
        acc = tl.zeros([BLOCK_N], dtype=ACCUM_DTYPE)
        
        for k_block in range(0, K, BLOCK_K):
            k_offs = k_block + tl.arange(0, BLOCK_K)
            k_mask = k_offs < K
            
            x_offset = row_idx * stride_xm + k_offs * stride_xk
            x = tl.load(x_ptr + x_offset, mask=k_mask, other=0.0).to(ACCUM_DTYPE)
            
            w_ptrs = w_ptr + k_offs[:, None] * stride_wk + col_offs[None, :] * stride_wn
            w = tl.load(w_ptrs, mask=k_mask[:, None] & col_mask[None, :], other=0.0).to(ACCUM_DTYPE)
            
            acc += tl.sum(x[:, None] * w, axis=0)
        
        # Add bias
        b = tl.load(b_ptr + col_offs, mask=col_mask, other=0.0).to(ACCUM_DTYPE)
        acc += b
        
        # Compute stable exp
        exp_acc = tl.exp(acc - row_max)
        sumexp += tl.sum(exp_acc, where=col_mask)
    
    # Compute final loss
    log_sumexp = tl.log(sumexp)
    loss = -target_logit + row_max + log_sumexp
    
    # Store result
    tl.store(output_ptr + row_idx * stride_out_m, loss)


def fused_linear_ce(
    X: torch.Tensor,
    W: torch.Tensor,
    B: torch.Tensor,
    targets: torch.Tensor,
) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    """
    # Input validation
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64
    
    M, K = X.shape
    N = W.shape[1]
    
    # Output tensor
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Choose kernel based on problem size
    if M <= 512:
        # Use single kernel for smaller batch sizes
        grid = (triton.cdiv(M, 1),)
        fused_linear_ce_single_kernel[grid](
            X, W, B, targets, output,
            M, K, N,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_M=1,
            BLOCK_K=64,
            BLOCK_N=128,
            ACCUM_DTYPE=tl.float32,
        )
    else:
        # Use multi-kernel approach for larger problems
        # Temporary storage
        temp_max = torch.empty(M, device=X.device, dtype=torch.float32)
        temp_sumexp = torch.empty(M, device=X.device, dtype=torch.float32)
        
        # First kernel: compute row max
        grid = (triton.cdiv(M, 64) * triton.cdiv(N, 128),)
        fused_linear_ce_kernel[grid](
            X, W, B, targets, output,  # output used as temp storage
            M, K, N,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_M=64,
            BLOCK_K=64,
            BLOCK_N=128,
            GROUP_M=8,
            ACCUM_DTYPE=tl.float32,
        )
        
        # Second kernel: compute sumexp and target logits
        fused_linear_ce_reduce_kernel[grid](
            X, W, B, targets, output,
            temp_max.data_ptr(), temp_sumexp.data_ptr(),
            M, K, N,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            output.stride(0),
            BLOCK_M=64,
            BLOCK_K=64,
            BLOCK_N=128,
            GROUP_M=8,
            ACCUM_DTYPE=tl.float32,
        )
        
        # Final kernel: compute loss
        final_grid = (triton.cdiv(M, 256),)
        fused_linear_ce_final_kernel[final_grid](
            output,
            temp_max.data_ptr(),
            temp_sumexp.data_ptr(),
            M, N,
            output.stride(0),
            BLOCK_M=256,
        )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    @staticmethod
    def _get_code() -> str:
        import inspect
        return inspect.getsource(fused_linear_ce)
