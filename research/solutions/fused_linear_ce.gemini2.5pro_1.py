import torch
import triton
import triton.language as tl

_fused_linear_ce_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 1, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 512, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _fused_linear_ce_forward_kernel_pass1(
    X, W, B, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    m_idx = tl.program_id(0)
    
    x_ptrs_base = X + m_idx * stride_xm
    
    row_max = -float('inf')
    
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_offsets = n_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N
        
        acc = tl.zeros((1, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_offsets = k_start * BLOCK_SIZE_K + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K
            
            x_ptrs = x_ptrs_base + k_offsets[None, :] * stride_xk
            x_tile = tl.load(x_ptrs, mask=k_mask[None, :], other=0.0)
            
            w_ptrs = W + k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn
            w_tile = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x_tile, w_tile, allow_tf32=True)
            
        b_ptrs = B + n_offsets
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits = acc + b_tile[None, :]
        
        current_max = tl.max(tl.where(n_mask[None, :], logits, -float('inf')), axis=1)
        row_max = tl.maximum(row_max, current_max)
        
    tl.store(L + m_idx, row_max)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 1, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 128, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _fused_linear_ce_forward_kernel_pass2(
    X, W, B, targets, O, L,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_target,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    m_idx = tl.program_id(0)
    
    x_ptrs_base = X + m_idx * stride_xm
    row_max = tl.load(L + m_idx)
    target_idx = tl.load(targets + m_idx * stride_target)
    
    # --- Sum exp part ---
    sum_exp = 0.0
    for n_start in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        n_offsets = n_start * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N
        
        acc = tl.zeros((1, BLOCK_SIZE_N), dtype=tl.float32)
        for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_offsets = k_start * BLOCK_SIZE_K + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K
            
            x_ptrs = x_ptrs_base + k_offsets[None, :] * stride_xk
            x_tile = tl.load(x_ptrs, mask=k_mask[None, :], other=0.0)
            
            w_ptrs = W + k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn
            w_tile = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x_tile, w_tile, allow_tf32=True)
            
        b_ptrs = B + n_offsets
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        
        logits = acc + b_tile[None, :]
        logits -= row_max
        
        sum_exp += tl.sum(tl.exp(tl.where(n_mask[None, :], logits, -float('inf'))))

    # --- Target logit part ---
    target_acc = tl.zeros((1,), dtype=tl.float32)
    for k_start in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        k_offsets = k_start * BLOCK_SIZE_K + tl.arange(0, BLOCK_SIZE_K)
        k_mask = k_offsets < K

        x_ptrs = x_ptrs_base + k_offsets * stride_xk
        x_tile = tl.load(x_ptrs, mask=k_mask, other=0.0)
        
        w_ptrs = W + k_offsets * stride_wk + target_idx * stride_wn
        w_tile = tl.load(w_ptrs, mask=k_mask, other=0.0)

        target_acc += tl.sum(x_tile.to(tl.float32) * w_tile.to(tl.float32))

    b_target = tl.load(B + target_idx)
    target_logit = target_acc + b_target
    
    # --- Final loss calculation ---
    loss = row_max + tl.log(sum_exp) - target_logit
    tl.store(O + m_idx, loss)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All tensors must be on CUDA"
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.int64, "targets must be int64"
    
    loss = torch.empty((M,), device=X.device, dtype=torch.float32)
    lse_max = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = (M,)

    _fused_linear_ce_forward_kernel_pass1[grid](
        X, W, B, lse_max,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
    )

    _fused_linear_ce_forward_kernel_pass2[grid](
        X, W, B, targets, loss, lse_max,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        targets.stride(0),
    )
    
    return loss
"""

exec(_fused_linear_ce_code)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _fused_linear_ce_code}