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
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32,  'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
        # Configurations with more parallelism in N
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=8),
        # Configurations with higher occupancy or more stages
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 32,  'BLOCK_SIZE_K': 128}, num_stages=3, num_warps=4),
        # Larger block sizes
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
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
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    # Each program instance computes the loss for a block of BLOCK_SIZE_M rows.
    pid_m = tl.program_id(axis=0)

    # Offsets for the M and K dimensions
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Pointers to the input tensor X.
    x_ptrs_base = X + offs_m[:, None] * stride_x_m + offs_k[None, :] * stride_x_k
    
    # Mask for valid rows (handling M not multiple of BLOCK_SIZE_M)
    m_mask = offs_m < M
    
    # Load target indices for the current block of rows
    target_indices = tl.load(targets + offs_m, mask=m_mask)

    # Initialize accumulators for the online softmax algorithm.
    # m_i: running maximum of logits
    # l_i: running sum of exp(logits - m_i)
    # target_logit: accumulator for the logit of the target class
    m_i = tl.full([BLOCK_SIZE_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_SIZE_M], dtype=tl.float32)
    target_logit = tl.zeros([BLOCK_SIZE_M], dtype=tl.float32)

    # --- Main loop over the N dimension in blocks of BLOCK_SIZE_N ---
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_start_offset = n_start * BLOCK_SIZE_N
        offs_n = n_start_offset + tl.arange(0, BLOCK_SIZE_N)
        n_mask = offs_n < N

        # --- Inner loop over the K dimension for matrix multiplication ---
        # Accumulator for the logit tile (X @ W)
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_start_offset = k_start * BLOCK_SIZE_K
            
            # Load a tile from X
            x_ptrs = x_ptrs_base + k_start_offset * stride_x_k
            x_mask = m_mask[:, None] & ((offs_k[None, :] + k_start_offset) < K)
            x_tile = tl.load(x_ptrs, mask=x_mask, other=0.0)
            
            # Load a tile from W
            w_ptrs = W + (offs_k[:, None] + k_start_offset) * stride_w_k + offs_n[None, :] * stride_w_n
            w_mask = ((offs_k[:, None] + k_start_offset) < K) & n_mask[None, :]
            w_tile = tl.load(w_ptrs, mask=w_mask, other=0.0)

            # Perform matrix multiplication and accumulate
            acc += tl.dot(x_tile, w_tile)
        
        # Add the bias vector
        b_ptrs = B + offs_n
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        # logits_tile now holds a block of logits
        logits_tile = acc + b_tile[None, :]
        
        # --- Online softmax update logic for numerical stability ---
        
        # Find the target logit if it falls within the current N-block
        target_mask = (offs_n[None, :] == target_indices[:, None])
        # Use sum as a reduction to extract the single value from the block
        target_logit += tl.sum(tl.where(target_mask, logits_tile, 0.0), axis=1)

        # Update the running max (m_i) and sum-exp (l_i)
        # 1. Find the max of the current logit tile
        m_curr = tl.max(tl.where(n_mask[None,:], logits_tile, -float('inf')), axis=1)
        # 2. Find the new overall max
        m_new = tl.maximum(m_i, m_curr)
        # 3. Rescale the running sum-exp accumulator
        alpha = tl.exp(m_i - m_new)
        # 4. Calculate the sum-exp of the current tile
        p = tl.exp(logits_tile - m_new[:, None])
        # 5. Update the running sum-exp
        l_i = l_i * alpha + tl.sum(tl.where(n_mask[None,:], p, 0.0), axis=1)
        # 6. Update the running max
        m_i = m_new

    # --- Final loss calculation ---
    # log-sum-exp = m + log(l)
    lse = m_i + tl.log(l_i)
    # cross-entropy loss = log-sum-exp - target_logit
    loss = lse - target_logit
    
    # Store the final loss to the output tensor
    out_ptrs = Out + offs_m * stride_o_m
    tl.store(out_ptrs, loss, mask=m_mask)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _K, N = W.shape
    
    if K != _K:
        raise ValueError(f"Dimension mismatch: X has {K} features, W expects {_K}")
    if B.shape[0] != N:
        raise ValueError(f"Dimension mismatch: B has {B.shape[0]} elements, expected {N}")
    if targets.shape[0] != M:
        raise ValueError(f"Dimension mismatch: targets has {targets.shape[0]} elements, expected {M}")

    # Allocate output tensor
    output = torch.empty((M,), device=X.device, dtype=torch.float32)

    # Grid for launching the kernel. Each program instance handles a block of rows.
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']),)

    # Launch the Triton kernel
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0)
    )
    
    return output
"""
        return {"code": code}