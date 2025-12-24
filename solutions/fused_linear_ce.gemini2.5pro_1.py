import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        _KERNEL_CODE = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64,  'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32,  'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64,  'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32,  'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64,  'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32, 'num_stages': 5, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
        # Configurations with larger BLOCK_K
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 4}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, O_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_om,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    # This kernel computes the cross-entropy loss for a batch of inputs.
    # It fuses the linear layer (X @ W + B) with the loss calculation.
    # The algorithm is a single-kernel, two-pass approach over the N dimension for each row block.

    # 1. KERNEL METADATA AND OFFSETS
    # Each program instance computes the loss for a block of BLOCK_M rows.
    pid_m = tl.program_id(0)
    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = m_offsets < M

    # Offsets for the K dimension, used in the inner loop of matmul
    k_base_offsets = tl.arange(0, BLOCK_K)
    
    # 2. LOAD TARGETS
    # Load the target class indices for the current block of rows.
    t_ptrs = T_ptr + m_offsets
    target_indices = tl.load(t_ptrs, mask=m_mask)

    # 3. PASS 1: FIND ROW-WISE MAXIMUM LOGIT
    # This is for numerical stability (log-sum-exp trick).
    # Initialize row_max to negative infinity.
    row_max = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)

    # Loop over the N dimension in blocks of BLOCK_N.
    for n_start in range(0, N, BLOCK_N):
        n_offsets = n_start + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N

        # Initialize accumulator for the matrix multiplication.
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        # Inner loop over the K dimension.
        for k_start in range(0, K, BLOCK_K):
            k_offsets = k_start + k_base_offsets
            
            # Load a tile of X.
            x_ptrs = X_ptr + m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk
            x = tl.load(x_ptrs, mask=(m_mask[:, None] & (k_offsets[None, :] < K)), other=0.0)
            
            # Load a tile of W.
            w_ptrs = W_ptr + k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn
            w = tl.load(w_ptrs, mask=((k_offsets[:, None] < K) & n_mask[None, :]), other=0.0)
            
            # Perform matrix multiplication.
            acc += tl.dot(x, w)

        # Load bias and add to accumulator to get logits.
        b_ptrs = B_ptr + n_offsets * stride_bn
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b

        # Update row_max.
        # Mask out-of-bounds logits before reduction to avoid affecting the max.
        logits_masked = tl.where(n_mask[None, :], logits, -float('inf'))
        block_max = tl.max(logits_masked, axis=1)
        row_max = tl.maximum(row_max, block_max)

    # 4. PASS 2: COMPUTE SUM_EXP and GATHER TARGET LOGIT
    # Initialize accumulators for the second pass.
    sum_exp = tl.zeros([BLOCK_M], dtype=tl.float32)
    target_logit = tl.zeros([BLOCK_M], dtype=tl.float32)

    # Loop over the N dimension again.
    for n_start in range(0, N, BLOCK_N):
        n_offsets = n_start + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N

        # Recompute logits for the current block.
        # (Recomputation is necessary as storing all logits would exceed SRAM).
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        for k_start in range(0, K, BLOCK_K):
            k_offsets = k_start + k_base_offsets
            x_ptrs = X_ptr + m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk
            x = tl.load(x_ptrs, mask=(m_mask[:, None] & (k_offsets[None, :] < K)), other=0.0)
            w_ptrs = W_ptr + k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn
            w = tl.load(w_ptrs, mask=((k_offsets[:, None] < K) & n_mask[None, :]), other=0.0)
            acc += tl.dot(x, w)
        
        b_ptrs = B_ptr + n_offsets * stride_bn
        b = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b

        # Find the logit corresponding to the target index for each row.
        target_mask = (n_offsets[None, :] == target_indices[:, None])
        # Summing with the mask effectively selects the target logit.
        # This accumulates over N; only one block will have a non-zero contribution.
        target_logit += tl.sum(tl.where(target_mask, logits, 0.0), axis=1)

        # Compute sum_exp part of the log-softmax.
        stable_logits = logits - row_max[:, None]
        # Mask out invalid values before exponentiating.
        stable_logits_masked = tl.where(n_mask[None, :], stable_logits, -float('inf'))
        sum_exp += tl.sum(tl.exp(stable_logits_masked), axis=1)

    # 5. FINAL LOSS CALCULATION
    # loss = -log(softmax(z))_target = log(sum_exp(z)) - z_target
    # loss = log(sum_exp(z-z_max)) + z_max - z_target
    loss = tl.log(sum_exp) + row_max - target_logit

    # 6. STORE RESULT
    o_ptrs = O_ptr + m_offsets * stride_om
    tl.store(o_ptrs, loss, mask=m_mask)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_W, N = W.shape
    
    # Input validation
    assert K == K_W, f"Mismatch in feature dimension K: X({K}) != W({K_W})"
    assert B.shape == (N,), f"B must have shape ({N},)"
    assert targets.shape == (M,), f"targets must have shape ({M},)"
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All tensors must be on CUDA device"
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.int64, "targets must be int64"

    # Allocate output tensor
    output = torch.empty(M, device=X.device, dtype=torch.float32)

    # Define the grid for kernel launch
    # Each program in the grid processes a block of rows
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']),)

    # Launch the kernel
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        output.stride(0),
    )

    return output
"""
        return {"code": _KERNEL_CODE}
