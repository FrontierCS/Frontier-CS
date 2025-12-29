import torch
import triton
import triton.language as tl

_fused_linear_jsd_code_str = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 2}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 2}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 3}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 32, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 64, 'num_stages': 2}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 32, 'num_stages': 2}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 128, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 128, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 4}, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1n,
    stride_b2n,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    # Each program computes the JSD for a single row of the input tensor X.
    pid = tl.program_id(axis=0)

    # Pointer to the start of the current row in X
    x_row_ptr = X_ptr + pid * stride_xm

    # --- Pass 1: Compute Log-Sum-Exp for both branches ---
    # This pass computes the normalization constant for the softmax in a numerically stable way.
    max1, sum1 = -float('inf'), 0.0
    max2, sum2 = -float('inf'), 0.0

    # Loop over the N dimension in blocks
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_offsets = (n_start * BLOCK_SIZE_N) + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N

        # Compute logits for the current block of N by accumulating over K
        acc1 = tl.zeros([BLOCK_SIZE_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_SIZE_N], dtype=tl.float32)
        
        # Loop over the K dimension in blocks (reduction)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_offsets = (k_start * BLOCK_SIZE_K) + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K

            # Load a tile from X for the current row
            x_ptr = x_row_ptr + k_offsets * stride_xk
            x_tile = tl.load(x_ptr, mask=k_mask, other=0.0)

            # Load tiles from W1 and W2
            w1_ptr = W1_ptr + (k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n)
            w1_tile = tl.load(w1_ptr, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            w2_ptr = W2_ptr + (k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n)
            w2_tile = tl.load(w2_ptr, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            # Perform matrix multiplication using tl.dot for Tensor Core acceleration
            acc1 = tl.dot(x_tile, w1_tile, acc1)
            acc2 = tl.dot(x_tile, w2_tile, acc2)

        # Add bias vectors
        b1_ptr = B1_ptr + n_offsets * stride_b1n
        b1_tile = tl.load(b1_ptr, mask=n_mask, other=0.0)
        logits1_tile = acc1 + b1_tile

        b2_ptr = B2_ptr + n_offsets * stride_b2n
        b2_tile = tl.load(b2_ptr, mask=n_mask, other=0.0)
        logits2_tile = acc2 + b2_tile

        # Update LSE components using an online algorithm for numerical stability
        current_max1 = tl.max(tl.where(n_mask, logits1_tile, -float('inf')), 0)
        new_max1 = tl.maximum(max1, current_max1)
        exp_val1 = tl.exp(logits1_tile - new_max1)
        sum1 = sum1 * tl.exp(max1 - new_max1) + tl.sum(tl.where(n_mask, exp_val1, 0.0), 0)
        max1 = new_max1

        current_max2 = tl.max(tl.where(n_mask, logits2_tile, -float('inf')), 0)
        new_max2 = tl.maximum(max2, current_max2)
        exp_val2 = tl.exp(logits2_tile - new_max2)
        sum2 = sum2 * tl.exp(max2 - new_max2) + tl.sum(tl.where(n_mask, exp_val2, 0.0), 0)
        max2 = new_max2

    lse1 = max1 + tl.log(sum1)
    lse2 = max2 + tl.log(sum2)

    # --- Pass 2: Compute Jensen-Shannon Divergence ---
    # This pass recomputes logits and uses the LSE values to compute probabilities and JSD.
    jsd_acc = 0.0
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_offsets = (n_start * BLOCK_SIZE_N) + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N

        # Re-compute logits for the current block
        acc1 = tl.zeros([BLOCK_SIZE_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_SIZE_N], dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_offsets = (k_start * BLOCK_SIZE_K) + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K

            x_ptr = x_row_ptr + k_offsets * stride_xk
            x_tile = tl.load(x_ptr, mask=k_mask, other=0.0)

            w1_ptr = W1_ptr + (k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n)
            w1_tile = tl.load(w1_ptr, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            w2_ptr = W2_ptr + (k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n)
            w2_tile = tl.load(w2_ptr, mask=k_mask[:, None] & n_mask[None, :], other=0.0)

            acc1 = tl.dot(x_tile, w1_tile, acc1)
            acc2 = tl.dot(x_tile, w2_tile, acc2)

        b1_ptr = B1_ptr + n_offsets * stride_b1n
        b1_tile = tl.load(b1_ptr, mask=n_mask, other=0.0)
        logits1_tile = acc1 + b1_tile

        b2_ptr = B2_ptr + n_offsets * stride_b2n
        b2_tile = tl.load(b2_ptr, mask=n_mask, other=0.0)
        logits2_tile = acc2 + b2_tile

        # Compute JSD components for the tile
        log_p = logits1_tile - lse1
        log_q = logits2_tile - lse2
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        
        m = 0.5 * (p + q)
        log_m = tl.log(m)
        
        kl_p_m_tile = p * (log_p - log_m)
        kl_q_m_tile = q * (log_q - log_m)
        
        # Accumulate JSD terms, handling cases where p or q are zero.
        jsd_tile = tl.where(p > 0, kl_p_m_tile, 0.0) + tl.where(q > 0, kl_q_m_tile, 0.0)
        jsd_acc += tl.sum(tl.where(n_mask, jsd_tile, 0.0), 0)

    # Final JSD value is scaled by 0.5
    final_jsd = 0.5 * jsd_acc
    out_ptr_row = Out_ptr + pid
    tl.store(out_ptr_row, final_jsd)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _K_w1, N = W1.shape
    
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Each program instance computes one row of the output.
    grid = (M,)

    # Launch the Triton kernel.
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0),
        B2.stride(0),
    )
    return output
"""

# Execute the kernel code string to define the functions
exec(_fused_linear_jsd_code_str)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _fused_linear_jsd_code_str}