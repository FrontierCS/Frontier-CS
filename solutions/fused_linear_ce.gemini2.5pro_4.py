import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        fused_kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations, balanced tile sizes
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32,  'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),

        # Configurations with larger N blocks, good for large vocabulary size
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),

        # Configurations with larger K blocks, good for large feature dimension
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128}, num_stages=3, num_warps=4),

        # More aggressive configurations for high occupancy
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X, W, B, targets, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_lm,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    # Each program instance computes the loss for a block of BLOCK_SIZE_M rows.
    pid = tl.program_id(axis=0)
    m_offs = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    m_mask = m_offs < M

    # Load target indices for the current block of rows.
    targets_ptrs = targets + m_offs
    target_idx = tl.load(targets_ptrs, mask=m_mask)

    # --- PASS 1: Compute row-wise max of logits for numerical stability ---
    row_max = tl.full((BLOCK_SIZE_M,), value=-float('inf'), dtype=tl.float32)
    
    # Iterate over the N dimension in blocks.
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_current_block_start = n_start * BLOCK_SIZE_N
        n_offs = n_current_block_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offs < N

        # --- Matrix Multiplication to get a tile of logits ---
        accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_current_block_start = k_start * BLOCK_SIZE_K
            k_offs = k_current_block_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offs < K

            x_ptrs = X + (m_offs[:, None] * stride_xm + k_offs[None, :] * stride_xk)
            x_tile = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            
            w_ptrs = W + (k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn)
            w_tile = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            accumulator = tl.dot(x_tile, w_tile, accumulator, out_dtype=tl.float32)

        b_ptrs = B + n_offs
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = accumulator + b_tile[None, :]

        # Update the running row-wise maximum.
        logits_masked_for_max = tl.where(m_mask[:, None] & n_mask[None, :], logits, -float('inf'))
        current_max = tl.max(logits_masked_for_max, axis=1)
        row_max = tl.maximum(row_max, current_max)

    # --- PASS 2: Compute log(sum(exp(logits - max))) and gather target logit ---
    sum_exp = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    target_logit = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)

    # Iterate over N again to re-compute logits for the second pass.
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_current_block_start = n_start * BLOCK_SIZE_N
        n_offs = n_current_block_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offs < N

        # Re-compute logits tile.
        accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_current_block_start = k_start * BLOCK_SIZE_K
            k_offs = k_current_block_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offs < K

            x_ptrs = X + (m_offs[:, None] * stride_xm + k_offs[None, :] * stride_xk)
            x_tile = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            
            w_ptrs = W + (k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn)
            w_tile = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            accumulator = tl.dot(x_tile, w_tile, accumulator, out_dtype=tl.float32)

        b_ptrs = B + n_offs
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = accumulator + b_tile[None, :]

        # Stabilize logits using the row_max from Pass 1.
        logits_stable = logits - row_max[:, None]
        exp_logits = tl.exp(logits_stable)
        exp_logits_masked = tl.where(m_mask[:, None] & n_mask[None, :], exp_logits, 0.0)
        sum_exp += tl.sum(exp_logits_masked, axis=1)

        # Gather the logit corresponding to the target index.
        target_mask = (n_offs[None, :] == target_idx[:, None])
        target_logit_tile = tl.sum(tl.where(target_mask & m_mask[:, None], logits, 0.0), axis=1)
        target_logit += target_logit_tile

    # --- FINAL CALCULATION: NLL Loss ---
    # NLL = max + log(sum(exp(logits - max))) - logits[target]
    log_sum_exp = tl.log(sum_exp)
    loss = row_max + log_sum_exp - target_logit

    # Store the final loss.
    L_ptrs = L + m_offs * stride_lm
    tl.store(L_ptrs, loss, mask=m_mask)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _K, N = W.shape
    
    # Input validation
    assert K == _K, f"Shape mismatch: X.shape[1] ({K}) != W.shape[0] ({_K})"
    assert W.shape[1] == B.shape[0], f"Shape mismatch: W.shape[1] ({N}) != B.shape[0] ({B.shape[0]})"
    assert X.shape[0] == targets.shape[0], f"Shape mismatch: X.shape[0] ({M}) != targets.shape[0] ({targets.shape[0]})"
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All tensors must be on CUDA device"
    assert X.dtype == torch.float16, "X tensor must be of type float16"
    assert W.dtype == torch.float16, "W tensor must be of type float16"
    assert B.dtype == torch.float32, "B tensor must be of type float32"
    assert targets.dtype == torch.int64, "targets tensor must be of type int64"

    L = torch.empty(M, device=X.device, dtype=torch.float32)

    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_SIZE_M']),)

    _fused_linear_ce_kernel[grid](
        X, W, B, targets, L,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        L.stride(0),
    )

    return L
"""
        return {"code": fused_kernel_code}
