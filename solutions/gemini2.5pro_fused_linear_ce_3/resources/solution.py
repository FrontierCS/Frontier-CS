import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations, balanced tile sizes
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 2048, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 4096, 'BLOCK_SIZE_K': 16, 'num_stages': 3, 'num_warps': 8}),
        
        # Configurations with different software pipelining depths (num_stages) and warp counts
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 2048, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 4096, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 2048, 'BLOCK_SIZE_K': 32, 'num_stages': 4, 'num_warps': 4}),
        
        # A configuration that processes the full N dimension in one block if N matches.
        # This avoids the outer loop over N, which can be very fast if it fits in registers.
        triton.Config({'BLOCK_SIZE_N': 8192, 'BLOCK_SIZE_K': 16, 'num_stages': 2, 'num_warps': 8}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_loss_m,
    BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    # Each program computes the loss for one row of X.
    pid_m = tl.program_id(axis=0)

    # =========================================================================
    # PASS 1: Compute row-wise maximum of logits for numerical stability.
    # The log-sum-exp trick requires subtracting the max logit value.
    # =========================================================================
    row_max = -float('inf')
    # Loop over the N dimension of W and B in blocks.
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offsets = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N
        
        # Accumulator for the dot product, initialized to zeros.
        # Computation is done in float32 for precision.
        acc = tl.zeros([BLOCK_SIZE_N], dtype=tl.float32)
        
        # Loop over the K dimension of X and W in blocks to compute matmul.
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K
            
            # Load a block of X and W.
            x_ptrs = X_ptr + pid_m * stride_xm + k_offsets * stride_xk
            x = tl.load(x_ptrs, mask=k_mask, other=0.0)
            
            w_ptrs = W_ptr + (k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            # Perform matrix multiplication. tl.dot uses Tensor Cores for fp16 inputs.
            acc += tl.dot(x, w)

        # Load and add the bias vector.
        b_ptrs = B_ptr + n_offsets
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits_block = acc + b
        
        # Update the running maximum for the row.
        block_max = tl.max(tl.where(n_mask, logits_block, -float('inf')), axis=0)
        row_max = tl.maximum(row_max, block_max)
    
    # =========================================================================
    # PASS 2: Recompute logits, calculate sum_exp and find the target logit.
    # This pass uses the computed `row_max` for stable calculations.
    # =========================================================================
    target_idx = tl.load(targets_ptr + pid_m)
    
    sum_exp = 0.0
    target_logit = -float('inf')
    
    # Loop over N again. Data for W will be re-streamed from HBM, but X and B
    # should have good cache locality.
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offsets = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N

        # Recompute the logit block. This is the trade-off for not materializing
        # the full logits tensor to global memory.
        acc = tl.zeros([BLOCK_SIZE_N], dtype=tl.float32)
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K
            
            x_ptrs = X_ptr + pid_m * stride_xm + k_offsets * stride_xk
            x = tl.load(x_ptrs, mask=k_mask, other=0.0)
            
            w_ptrs = W_ptr + (k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x, w)
        
        b_ptrs = B_ptr + n_offsets
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits_block = acc + b

        # Apply the log-sum-exp trick for numerical stability.
        logits_minus_max = logits_block - row_max
        exp_logits = tl.exp(logits_minus_max)
        
        # Accumulate the sum of exponents.
        sum_exp += tl.sum(tl.where(n_mask, exp_logits, 0.0), axis=0)
        
        # Find the logit corresponding to the target index.
        # This emulates a gather operation by checking which block contains the index.
        target_mask = (n_offsets == target_idx)
        current_block_target_logit = tl.max(tl.where(target_mask, logits_block, -float('inf')), axis=0)
        target_logit = tl.maximum(target_logit, current_block_target_logit)

    # =========================================================================
    # Final loss computation: loss = -log(softmax(z)_i) = log(sum(exp(z))) - z_i
    # =========================================================================
    log_sum_exp = row_max + tl.log(sum_exp)
    loss = log_sum_exp - target_logit
    
    # Store the final loss value for the row.
    loss_ptrs = loss_ptr + pid_m * stride_loss_m
    tl.store(loss_ptrs, loss)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Fused linear layer with cross entropy loss computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    \"\"\"
    M, K = X.shape
    _K, N = W.shape
    
    # Create the output tensor for the loss.
    loss = torch.empty(M, device=X.device, dtype=torch.float32)

    # Define the grid for the kernel launch. 1D grid of size M.
    # Each program instance computes one loss value.
    grid = (M, )

    # Launch the Triton kernel.
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, loss,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        loss.stride(0),
    )
    return loss
"""
        return {"code": code}
