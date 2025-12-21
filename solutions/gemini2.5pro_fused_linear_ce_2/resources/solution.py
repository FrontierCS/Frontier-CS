import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 4}),
        
        # Configurations with larger K block
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        
        # Configurations with more warps and stages
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'num_stages': 4, 'num_warps': 8}),

        # Balanced configurations
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        
        # Larger M and N blocks
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X, W, B, targets, Out,
    M, N, K,
    stride_x_m, stride_x_k,
    stride_w_k, stride_w_n,
    stride_o_m,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr
):
    # Each program instance computes the loss for a block of M rows.
    pid_m = tl.program_id(axis=0)

    # Compute offsets for the block of rows this program will handle.
    m_offsets = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    m_mask = m_offsets < M

    # Pointers to the target indices for the current block of rows.
    targets_ptrs = targets + m_offsets
    target_indices = tl.load(targets_ptrs, mask=m_mask)

    # Initialize accumulators for the numerically stable online softmax.
    # `row_max` tracks the running maximum logit for each row.
    row_max = tl.full((BLOCK_SIZE_M,), -float('inf'), dtype=tl.float32)
    # `row_sum_exp` tracks the running sum of exponentiated logits, scaled by the max.
    row_sum_exp = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    # `target_logit` will store the logit value for the target class index.
    target_logit = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)

    # Iterate over the N dimension (columns of W/logits) in blocks.
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offsets = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N

        # --- Matrix Multiplication: Compute a tile of logits ---
        # Initialize accumulator for the (BLOCK_SIZE_M, BLOCK_SIZE_N) logit tile.
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        
        # Iterate over the K dimension (inner dimension of matmul) in blocks.
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask_1d = k_offsets < K

            # Pointers to tiles in X and W.
            x_ptrs = X + (m_offsets[:, None] * stride_x_m + k_offsets[None, :] * stride_x_k)
            w_ptrs = W + (k_offsets[:, None] * stride_w_k + n_offsets[None, :] * stride_w_n)

            # Load tiles from X and W, masking out-of-bounds elements.
            x_tile = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask_1d[None, :], other=0.0)
            w_tile = tl.load(w_ptrs, mask=k_mask_1d[:, None] & n_mask[None, :], other=0.0)

            # Perform matrix multiplication on tiles and accumulate the result.
            # tl.dot uses tensor cores for float16 inputs.
            acc = tl.dot(x_tile, w_tile, acc)
        
        # Add bias vector B to the computed logit tile.
        b_ptrs = B + n_offsets
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits_tile = acc + b_tile.to(tl.float32)[None, :]

        # --- Fused Cross-Entropy Calculation ---
        
        # Find and accumulate the logit corresponding to the target index.
        target_in_tile_mask = (target_indices[:, None] == n_offsets[None, :])
        current_target_logit = tl.sum(logits_tile * target_in_tile_mask, axis=1)
        target_logit += current_target_logit

        # --- Numerically Stable Online Softmax Update ---
        # This part implements the "two-pass" logic in a single pass over N.
        
        # 1. Find the maximum of the current logit tile.
        masked_logits_tile = tl.where(m_mask[:, None] & n_mask[None, :], logits_tile, -float('inf'))
        tile_max = tl.max(masked_logits_tile, axis=1)
        
        # 2. Update the overall row-wise maximum.
        new_max = tl.maximum(row_max, tile_max)
        
        # 3. Rescale the running sum_exp and add the contribution from the new tile.
        exp_logits = tl.exp(logits_tile - new_max[:, None])
        exp_logits = tl.where(m_mask[:, None] & n_mask[None, :], exp_logits, 0.0)
        tile_sum_exp = tl.sum(exp_logits, axis=1)
        
        # The core online update formula.
        row_sum_exp = row_sum_exp * tl.exp(row_max - new_max) + tile_sum_exp
        row_max = new_max

    # --- Final Loss Computation ---
    # After iterating through all N blocks, compute the final loss for each row.
    log_sum_exp = row_max + tl.log(row_sum_exp)
    loss = log_sum_exp - target_logit
    
    # Write the final loss to the output tensor.
    out_ptrs = Out + m_offsets * stride_o_m
    tl.store(out_ptrs, loss, mask=m_mask)


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
    if W.shape[0] != K:
        raise ValueError(f"Incompatible dimensions: X has {K} features, but W has {W.shape[0]} inputs")
    N = W.shape[1]
    if B.shape[0] != N:
        raise ValueError(f"Incompatible dimensions: W has {N} outputs, but B has {B.shape[0]} elements")
    if targets.shape[0] != M:
        raise ValueError(f"Incompatible dimensions: X has batch size {M}, but targets has {targets.shape[0]}")

    # Allocate output tensor.
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # The grid is 1D, with one program instance per BLOCK_SIZE_M rows.
    # The META object contains the autotuned block sizes.
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']),)
    
    # Launch the Triton kernel.
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0),
    )
    
    return output
"""
        return {"code": code}
