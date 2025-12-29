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
        # Basic configs
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 64, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 128, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 32, 'num_warps': 4}),

        # More aggressive configs for larger N
        triton.Config({'BLOCK_SIZE_N': 2048, 'BLOCK_SIZE_K': 64, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 128, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 2048, 'BLOCK_SIZE_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 4096, 'BLOCK_SIZE_K': 32, 'num_warps': 16}),

        # Configs tuned for smaller K
        triton.Config({'BLOCK_SIZE_N': 1024, 'BLOCK_SIZE_K': 16, 'num_warps': 4}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _fused_jsd_kernel(
    # Pointers to matrices
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    Logits1_ptr, Logits2_ptr, Out_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    stride_out,
    # Meta-parameters
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)

    # Pointers to the current row for this program
    x_row_ptr = X_ptr + pid_m * stride_xm
    l1_row_ptr = Logits1_ptr + pid_m * stride_l1m
    l2_row_ptr = Logits2_ptr + pid_m * stride_l2m

    # === STAGE 1: Compute and store logits to temporary global memory ===
    for n_block_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n = n_block_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        mask_n = offs_n < N
        
        acc1 = tl.zeros((BLOCK_SIZE_N,), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_SIZE_N,), dtype=tl.float32)
        
        for k_block_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            offs_k = k_block_start * BLOCK_SIZE_K + tl.arange(0, BLOCK_SIZE_K)
            mask_k = offs_k < K
            
            x_ptrs = x_row_ptr + offs_k * stride_xk
            x = tl.load(x_ptrs, mask=mask_k, other=0.0)
            
            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
            
            w1 = tl.load(w1_ptrs, mask=(mask_k[:, None] & mask_n[None, :]), other=0.0)
            w2 = tl.load(w2_ptrs, mask=(mask_k[:, None] & mask_n[None, :]), other=0.0)
            
            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)
            
        b1_ptrs = B1_ptr + offs_n
        b2_ptrs = B2_ptr + offs_n
        b1 = tl.load(b1_ptrs, mask=mask_n, other=0.0)
        b2 = tl.load(b2_ptrs, mask=mask_n, other=0.0)
        
        logits1_block = acc1 + b1
        logits2_block = acc2 + b2
        
        l1_block_ptr = l1_row_ptr + offs_n
        l2_block_ptr = l2_row_ptr + offs_n
        tl.store(l1_block_ptr, logits1_block, mask=mask_n)
        tl.store(l2_block_ptr, logits2_block, mask=mask_n)

    # === STAGE 2: Compute Log-Sum-Exp from temporary logits ===
    # This is a two-pass reduction over the N dimension for the current row.
    max_val1 = -float('inf')
    max_val2 = -float('inf')
    
    # First pass: find max
    for n_block_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n = n_block_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        mask_n = offs_n < N
        
        l1_block = tl.load(l1_row_ptr + offs_n, mask=mask_n, other=-float('inf'))
        l2_block = tl.load(l2_row_ptr + offs_n, mask=mask_n, other=-float('inf'))
        
        max_val1 = tl.maximum(max_val1, tl.max(l1_block, 0))
        max_val2 = tl.maximum(max_val2, tl.max(l2_block, 0))

    # Second pass: compute sum of exps
    lse_sum1 = 0.0
    lse_sum2 = 0.0
    for n_block_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n = n_block_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        mask_n = offs_n < N
        
        l1_block = tl.load(l1_row_ptr + offs_n, mask=mask_n, other=-float('inf'))
        l2_block = tl.load(l2_row_ptr + offs_n, mask=mask_n, other=-float('inf'))
        
        lse_sum1 += tl.sum(tl.exp(l1_block - max_val1), 0)
        lse_sum2 += tl.sum(tl.exp(l2_block - max_val2), 0)
        
    lse1 = max_val1 + tl.log(lse_sum1)
    lse2 = max_val2 + tl.log(lse_sum2)
    
    # === STAGE 3: Compute JSD from temporary logits and LSE values ===
    kl_pm_sum = 0.0
    kl_qm_sum = 0.0
    log_half = tl.log(0.5)

    for n_block_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        offs_n = n_block_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        mask_n = offs_n < N
        
        logits1_block = tl.load(l1_row_ptr + offs_n, mask=mask_n, other=-float('inf'))
        logits2_block = tl.load(l2_row_ptr + offs_n, mask=mask_n, other=-float('inf'))
        
        log_p_block = logits1_block - lse1
        log_q_block = logits2_block - lse2
        
        p_block = tl.exp(log_p_block)
        q_block = tl.exp(log_q_block)
        
        # Numerically stable log_m_block computation
        max_log_pq = tl.maximum(log_p_block, log_q_block)
        safe_max_log_pq = tl.where(max_log_pq > -1e38, max_log_pq, 0.0)
        log_m_denom = tl.exp(log_p_block - safe_max_log_pq) + tl.exp(log_q_block - safe_max_log_pq)
        log_m_block = log_half + safe_max_log_pq + tl.where(log_m_denom > 1e-38, tl.log(log_m_denom), -1e38)
        
        kl_pm_term = p_block * (log_p_block - log_m_block)
        kl_qm_term = q_block * (log_q_block - log_m_block)
        
        # Mask out terms where p or q are zero to avoid 0 * -inf = nan
        kl_pm_term = tl.where(p_block > 1e-38, kl_pm_term, 0.0)
        kl_qm_term = tl.where(q_block > 1e-38, kl_qm_term, 0.0)
        
        kl_pm_sum += tl.sum(tl.where(mask_n, kl_pm_term, 0.0), 0)
        kl_qm_sum += tl.sum(tl.where(mask_n, kl_qm_term, 0.0), 0)
        
    jsd = 0.5 * (kl_pm_sum + kl_qm_sum)
    
    out_ptr = Out_ptr + pid_m * stride_out
    tl.store(out_ptr, jsd)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)
    
    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    \"\"\"
    M, K = X.shape
    _, N = W1.shape
    
    # Allocate temporary buffers for logits and the final output
    logits1 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    logits2 = torch.empty((M, N), device=X.device, dtype=torch.float32)
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Each program computes one JSD value for one row of X
    grid = (M,)
    
    _fused_jsd_kernel[grid](
        X, W1, B1, W2, B2,
        logits1, logits2, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        output.stride(0),
    )
    
    return output
"""
        return {"code": code}