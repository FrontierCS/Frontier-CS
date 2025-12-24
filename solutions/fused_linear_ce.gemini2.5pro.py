import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

_AUTOTUNE_CONFIGS = [
    triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 16, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64}, num_stages=3, num_warps=4),
    triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_SIZE_M': 32, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=8),
    triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32}, num_stages=4, num_warps=8),
]

@triton.autotune(
    configs=_AUTOTUNE_CONFIGS,
    key=['M', 'N', 'K'],
)
@triton.jit
def _get_rowmax_kernel(
    X_ptr, W_ptr, B_ptr, RowMax_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_rm,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    m_offsets = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    m_mask = m_offsets < M
    
    row_max = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32) - float('inf')
    
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offsets = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N
        
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K
            
            x_ptrs = X_ptr + (m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk)
            w_ptrs = W_ptr + (k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn)
            
            x_tile = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w_tile = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x_tile, w_tile)
            
        b_ptrs = B_ptr + n_offsets * stride_b
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        
        logits_tile = acc + b_tile[None, :]
        logits_tile = tl.where(n_mask[None, :], logits_tile, -float('inf'))
        
        tile_max = tl.max(logits_tile, axis=1)
        row_max = tl.maximum(row_max, tile_max)
        
    rm_ptrs = RowMax_ptr + m_offsets * stride_rm
    tl.store(rm_ptrs, row_max, mask=m_mask)

@triton.autotune(
    configs=_AUTOTUNE_CONFIGS,
    key=['M', 'N', 'K'],
)
@triton.jit
def _compute_loss_kernel(
    X_ptr, W_ptr, B_ptr, Targets_ptr, RowMax_ptr, Loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_t,
    stride_rm,
    stride_l,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    m_offsets = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    m_mask = m_offsets < M
    
    rm_ptrs = RowMax_ptr + m_offsets * stride_rm
    row_maxes = tl.load(rm_ptrs, mask=m_mask)
    
    t_ptrs = Targets_ptr + m_offsets * stride_t
    target_indices = tl.load(t_ptrs, mask=m_mask)
    
    sum_exp = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    target_logits = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_SIZE_N):
        n_offsets = n_start + tl.arange(0, BLOCK_SIZE_N)
        n_mask = n_offsets < N
        
        acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        
        for k_start in range(0, K, BLOCK_SIZE_K):
            k_offsets = k_start + tl.arange(0, BLOCK_SIZE_K)
            k_mask = k_offsets < K
            
            x_ptrs = X_ptr + (m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk)
            w_ptrs = W_ptr + (k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn)
            
            x_tile = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w_tile = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc += tl.dot(x_tile, w_tile)
            
        b_ptrs = B_ptr + n_offsets * stride_b
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        
        logits_tile = acc + b_tile[None, :]
        
        target_mask = (n_offsets[None, :] == target_indices[:, None])
        target_logits += tl.sum(tl.where(target_mask & n_mask[None, :], logits_tile, 0.0), axis=1)

        logits_tile_stable = logits_tile - row_maxes[:, None]
        exp_tile = tl.exp(tl.where(n_mask[None, :], logits_tile_stable, -float('inf')))
        sum_exp += tl.sum(exp_tile, axis=1)
        
    log_sum_exp = row_maxes + tl.log(sum_exp)
    loss = log_sum_exp - target_logits
    
    l_ptrs = Loss_ptr + m_offsets * stride_l
    tl.store(l_ptrs, loss, mask=m_mask)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]

    loss = torch.empty((M,), dtype=torch.float32, device=X.device)
    row_max = torch.empty((M,), dtype=torch.float32, device=X.device)

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_SIZE_M']),)
    
    _get_rowmax_kernel[grid](
        X, W, B, row_max,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        row_max.stride(0)
    )

    _compute_loss_kernel[grid](
        X, W, B, targets, row_max, loss,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        targets.stride(0),
        row_max.stride(0),
        loss.stride(0)
    )
    
    return loss
"""
        return {"code": kernel_code}
