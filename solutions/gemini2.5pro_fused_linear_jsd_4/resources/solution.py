import torch
import triton
import triton.language as tl
import inspect

# This string contains the full implementation that will be passed to the evaluator.
_triton_kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations with varying block sizes and warp counts
        triton.Config({'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        # Configurations with more warps for higher occupancy and parallelism
        triton.Config({'BLOCK_K': 32, 'num_stages': 4, 'num_warps': 16}),
        triton.Config({'BLOCK_K': 64, 'num_stages': 4, 'num_warps': 16}),
        # Configurations with larger K blocks for more work per thread
        triton.Config({'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 16}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1n, stride_b2n,
    stride_outm,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    '''
    Triton kernel for fused linear layers and Jensen-Shannon Divergence.
    Each program in the grid computes the JSD for a single row of the input tensor X.
    The kernel is structured as follows:
    1. Compute two full logit vectors (size N) by performing two matrix-vector multiplications.
       This is done by tiling over the K dimension.
    2. Compute softmax probabilities P and Q using a stable log-sum-exp approach.
       This involves block-level reductions (tl.max, tl.sum) over the N dimension.
    3. Compute the JSD using the formula: JSD = H(M) - 0.5 * (H(P) + H(Q)),
       where M = 0.5 * (P + Q) and H is the Shannon entropy.
    4. Handle numerical stability for log(0) by adding a small epsilon.
    '''
    # Each program instance computes one JSD value for one row of X.
    pid_m = tl.program_id(axis=0)

    # --- Step 1: Compute logits1 and logits2 for the current row ---
    n_offsets = tl.arange(0, BLOCK_N)
    
    # Accumulators for the two matmuls, initialized to zero.
    acc1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_N,), dtype=tl.float32)
    
    # Loop over the K dimension in blocks to compute the matrix-vector products.
    for k_start in range(0, K, BLOCK_K):
        k_offsets = k_start + tl.arange(0, BLOCK_K)
        k_mask = k_offsets < K
        
        # Load a tile of X for the current row. Shape: (BLOCK_K,)
        x_ptrs = X_ptr + pid_m * stride_xm + k_offsets * stride_xk
        # Cast input to float32 for high-precision accumulation
        x = tl.load(x_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Load tiles of W1 and W2. Shape: (BLOCK_K, BLOCK_N)
        w1_ptrs = W1_ptr + (k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n)
        w1 = tl.load(w1_ptrs, mask=k_mask[:, None], other=0.0)
        
        w2_ptrs = W2_ptr + (k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n)
        w2 = tl.load(w2_ptrs, mask=k_mask[:, None], other=0.0)
        
        # Accumulate dot product. Triton handles upcasting of W1/W2 to float32.
        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)
    
    # Add biases to the accumulated values to get the final logits.
    b1_ptrs = B1_ptr + n_offsets * stride_b1n
    b1 = tl.load(b1_ptrs, mask=n_offsets < N, other=0.0)
    logits1 = acc1 + b1
    
    b2_ptrs = B2_ptr + n_offsets * stride_b2n
    b2 = tl.load(b2_ptrs, mask=n_offsets < N, other=0.0)
    logits2 = acc2 + b2

    # --- Step 2: Compute P = softmax(logits1) and Q = softmax(logits2) stablely ---
    # Use the log-sum-exp trick for numerical stability.
    # `log_softmax(x) = x - logsumexp(x)`
    # `logsumexp(x) = max(x) + log(sum(exp(x - max(x))))`
    
    # For P
    max1 = tl.max(logits1, axis=0)
    lse1 = max1 + tl.log(tl.sum(tl.exp(logits1 - max1), axis=0))
    log_p = logits1 - lse1
    p = tl.exp(log_p)

    # For Q
    max2 = tl.max(logits2, axis=0)
    lse2 = max2 + tl.log(tl.sum(tl.exp(logits2 - max2), axis=0))
    log_q = logits2 - lse2
    q = tl.exp(log_q)

    # --- Step 3: Compute M and JSD ---
    # JSD = H(M) - 0.5 * (H(P) + H(Q))
    # H(X) = -sum(X * log(X))
    
    m = 0.5 * (p + q)

    # Entropy terms: H(P) and H(Q). p*log(p) is numerically stable since p is from exp.
    h_p_term = p * log_p
    h_q_term = q * log_q
    
    # For H(M), we need log(m). Add a small epsilon to avoid log(0) -> -inf,
    # which would cause `m * log(m)` -> `0 * -inf = nan`.
    log_m = tl.log(m + 1e-20)
    h_m_term = m * log_m
    
    # Reduce over the N dimension to get the scalar entropy values.
    h_p = -tl.sum(h_p_term, axis=0)
    h_q = -tl.sum(h_q_term, axis=0)
    h_m = -tl.sum(h_m_term, axis=0)

    # Final JSD calculation.
    jsd = h_m - 0.5 * (h_p + h_q)

    # Store the final result for the current row.
    out_ptrs = Out_ptr + pid_m * stride_outm
    tl.store(out_ptrs, jsd)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)
    
    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    M, K = X.shape
    _K1, N = W1.shape
    
    # Create the output tensor.
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # The grid is 1D, with one program per row of X.
    grid = (M,)
    
    # This implementation fixes BLOCK_N = N. This is efficient when N is a power of 2
    # and the entire logits vector (size N) fits into the SM's shared memory / registers.
    # Given the problem constraints (N=4096), this is a feasible approach.
    
    # Launch the Triton kernel.
    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0),
        B2.stride(0),
        output.stride(0),
        BLOCK_N=N,
        # BLOCK_K, num_stages, and num_warps are determined by the autotuner.
    )
    
    return output
"""

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Triton kernel code.
        """
        return {"code": _triton_kernel_code}
