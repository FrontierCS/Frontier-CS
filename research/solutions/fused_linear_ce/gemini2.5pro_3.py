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
        
        fused_kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_N': 64,  'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        
        # Configurations with more stages and warps for better latency hiding
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 512, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),

        # Configurations with larger K blocks for better data reuse
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 128, 'num_stages': 2, 'num_warps': 8}),

        # Configurations with very large N blocks
        triton.Config({'BLOCK_N': 1024, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_N': 1024, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_N': 2048, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _fused_kernel(
    X, W, B, targets, output,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)

    # Pointer to the start of the current row in X
    x_ptr = X + pid_m * stride_xm
    
    # Get the target index for the current row
    target_idx = tl.load(targets + pid_m)

    # --- Step 1: Compute the logit for the target class ---
    # This is a dot product: X[pid_m, :] @ W[:, targets[pid_m]]
    target_acc = 0.0
    w_target_ptr = W + target_idx * stride_wn
    for k_start in range(0, K, BLOCK_K):
        k_offsets = k_start + tl.arange(0, BLOCK_K)
        k_mask = k_offsets < K
        
        x_tile = tl.load(x_ptr + k_offsets * stride_xk, mask=k_mask, other=0.0)
        w_tile = tl.load(w_target_ptr + k_offsets * stride_wk, mask=k_mask, other=0.0)
        
        target_acc += tl.sum(x_tile * w_tile)
    
    target_logit = target_acc + tl.load(B + target_idx)

    # --- Step 2: Compute log(sum(exp(logits))) using online softmax ---
    m_i = -float('inf')
    s_i = 0.0

    # Iterate over the N dimension in blocks
    for n_start in range(0, N, BLOCK_N):
        n_offsets = n_start + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N
        
        # Compute a tile of logits: X[pid_m, :] @ W[:, n_offsets]
        acc = tl.zeros((BLOCK_N,), dtype=tl.float32)
        for k_start in range(0, K, BLOCK_K):
            k_offsets_k = k_start + tl.arange(0, BLOCK_K)
            k_mask_k = k_offsets_k < K
            
            x_tile = tl.load(x_ptr + k_offsets_k * stride_xk, mask=k_mask_k, other=0.0)
            
            w_ptr = W + (k_offsets_k[:, None] * stride_wk + n_offsets[None, :] * stride_wn)
            w_mask = k_mask_k[:, None] & n_mask[None, :]
            w_tile = tl.load(w_ptr, mask=w_mask, other=0.0)
            
            acc += tl.dot(x_tile, w_tile)

        b_tile = tl.load(B + n_offsets, mask=n_mask, other=0.0)
        logits = acc + b_tile

        # Update online statistics
        m_ij = tl.max(logits, axis=0)
        m_i_new = tl.maximum(m_i, m_ij)
        
        s_i = s_i * tl.exp(m_i - m_i_new)
        p_ij = tl.exp(logits - m_i_new)
        s_i += tl.sum(p_ij, axis=0)
        
        m_i = m_i_new

    # --- Step 3: Final loss calculation ---
    log_sum_exp = tl.log(s_i) + m_i
    loss = log_sum_exp - target_logit
    
    tl.store(output + pid_m * stride_om, loss)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _K, N = W.shape
    
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    grid = (M, )
    
    _fused_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0),
    )
    
    return output
"""
        return {"code": fused_kernel_code}