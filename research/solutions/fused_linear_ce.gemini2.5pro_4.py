import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code_string = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_K': 32, 'BLOCK_N_TILE': 64, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 64, 'BLOCK_N_TILE': 64, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 32, 'BLOCK_N_TILE': 128, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 64, 'BLOCK_N_TILE': 128, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 32, 'BLOCK_N_TILE': 256, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 64, 'BLOCK_N_TILE': 256, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 128, 'BLOCK_N_TILE': 128, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 64, 'BLOCK_N_TILE': 512, 'num_warps': 16, 'num_stages': 2}),
        triton.Config({'BLOCK_K': 128, 'BLOCK_N_TILE': 256, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_K': 256, 'BLOCK_N_TILE': 128, 'num_warps': 8, 'num_stages': 3}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, Out_ptr,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_xm: tl.int32, stride_xk: tl.int32,
    stride_wk: tl.int32, stride_wn: tl.int32,
    BLOCK_K: tl.constexpr,
    BLOCK_N_TILE: tl.constexpr,
):
    pid_m = tl.program_id(0)

    x_row_ptr = X_ptr + pid_m * stride_xm
    target_ptr = targets_ptr + pid_m
    out_ptr = Out_ptr + pid_m

    # Pass 1: find max
    m_i = tl.full(shape=(), fill_value=-float('inf'), dtype=tl.float32)
    
    # Iterate over N dimension by tiles
    for n_start_idx in range(0, tl.cdiv(N, BLOCK_N_TILE)):
        n_start = n_start_idx * BLOCK_N_TILE
        n_offsets = n_start + tl.arange(0, BLOCK_N_TILE)
        n_mask = n_offsets < N

        # Compute a tile of logits
        acc = tl.zeros((BLOCK_N_TILE,), dtype=tl.float32)
        for k_start_idx in range(0, tl.cdiv(K, BLOCK_K)):
            k_start = k_start_idx * BLOCK_K
            k_offsets = k_start + tl.arange(0, BLOCK_K)
            k_mask = k_offsets < K
            
            x_ptrs = x_row_ptr + k_offsets
            x_tile = tl.load(x_ptrs, mask=k_mask, other=0.0)
            
            w_ptrs = W_ptr + k_offsets[:, None] * stride_wk + n_offsets[None, :]
            w_mask = k_mask[:, None] & n_mask[None, :]
            w_tile = tl.load(w_ptrs, mask=w_mask, other=0.0)
            
            acc += tl.dot(x_tile, w_tile)

        b_ptrs = B_ptr + n_offsets
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits_tile = acc + b_tile

        masked_logits = tl.where(n_mask, logits_tile, -float('inf'))
        tile_max = tl.max(masked_logits, axis=0)
        m_i = tl.maximum(m_i, tile_max)

    # Pass 2: compute sum_exp and target_logit
    sum_exp = tl.zeros(shape=(), dtype=tl.float32)
    target = tl.load(target_ptr)
    target_logit = tl.zeros(shape=(), dtype=tl.float32)
    
    for n_start_idx in range(0, tl.cdiv(N, BLOCK_N_TILE)):
        n_start = n_start_idx * BLOCK_N_TILE
        n_offsets = n_start + tl.arange(0, BLOCK_N_TILE)
        n_mask = n_offsets < N

        # Recompute logits_tile
        acc = tl.zeros((BLOCK_N_TILE,), dtype=tl.float32)
        for k_start_idx in range(0, tl.cdiv(K, BLOCK_K)):
            k_start = k_start_idx * BLOCK_K
            k_offsets = k_start + tl.arange(0, BLOCK_K)
            k_mask = k_offsets < K

            x_ptrs = x_row_ptr + k_offsets
            x_tile = tl.load(x_ptrs, mask=k_mask, other=0.0)
            
            w_ptrs = W_ptr + k_offsets[:, None] * stride_wk + n_offsets[None, :]
            w_mask = k_mask[:, None] & n_mask[None, :]
            w_tile = tl.load(w_ptrs, mask=w_mask, other=0.0)
            
            acc += tl.dot(x_tile, w_tile)
        
        b_ptrs = B_ptr + n_offsets
        b_tile = tl.load(b_ptrs, mask=n_mask, other=0.0)
        logits_tile = acc + b_tile
        
        # Update sum_exp
        stable_logits = logits_tile - m_i
        exp_tile = tl.exp(stable_logits)
        masked_exps = tl.where(n_mask, exp_tile, 0.0)
        sum_exp += tl.sum(masked_exps, axis=0)
        
        # Update target_logit
        target_mask = n_offsets == target
        target_logit += tl.sum(logits_tile * target_mask.to(logits_tile.dtype), axis=0)

    # Final loss calculation
    loss = m_i + tl.log(sum_exp) - target_logit
    tl.store(out_ptr, loss)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    
    output = torch.empty(M, device=X.device, dtype=torch.float32)

    grid = lambda META: (M,)

    _fused_linear_ce_kernel[grid](
        X, W, B, targets, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
    )

    return output
"""
        return {"code": kernel_code_string}