import sys
import os
import torch
import flashinfer
import triton
import triton.language as tl

@triton.jit
def _fused_rmsnorm_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    stride_q_row, stride_q_col,
    stride_k_row, stride_k_col,
    stride_qo_row, stride_qo_col,
    stride_ko_row, stride_ko_col,
    stride_w,
    N_q, N_k, D,
    eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Determine if we are processing Q or K
    if pid < N_q:
        # Process Q row
        row_idx = pid
        base_ptr = Q_ptr + row_idx * stride_q_row
        out_base_ptr = Q_out_ptr + row_idx * stride_qo_row
        stride_col = stride_q_col
        stride_out_col = stride_qo_col
    elif pid < N_q + N_k:
        # Process K row
        row_idx = pid - N_q
        base_ptr = K_ptr + row_idx * stride_k_row
        out_base_ptr = K_out_ptr + row_idx * stride_ko_row
        stride_col = stride_k_col
        stride_out_col = stride_ko_col
    else:
        return

    cols = tl.arange(0, BLOCK_SIZE)
    mask = cols < D
    
    # Compute offsets
    offsets = cols * stride_col
    w_offsets = cols * stride_w
    out_offsets = cols * stride_out_col
    
    # Load input
    x = tl.load(base_ptr + offsets, mask=mask, other=0.0).to(tl.float32)
    
    # Load weight (broadcasted)
    w = tl.load(W_ptr + w_offsets, mask=mask, other=0.0).to(tl.float32)
    
    # RMSNorm computation
    x_sq = x * x
    mean_sq = tl.sum(x_sq, axis=0) / D
    rstd = tl.rsqrt(mean_sq + eps)
    
    y = x * rstd * w
    
    # Store output
    tl.store(out_base_ptr + out_offsets, y, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors efficiently.
    Attempts to fuse Q and K operations if shapes allow view as (N, D).
    Falls back to flashinfer for complex strided layouts.
    """
    D = norm_weight.shape[0]
    eps = 1e-6
    
    # Allocate output tensors. We use empty (contiguous) for performance.
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    # Try to view inputs as 2D (-1, D) to enable fused kernel
    # This works if the tensors are contiguous or have compatible strides
    try:
        q_2d = q.view(-1, D)
        k_2d = k.view(-1, D)
        q_o_2d = q_o.view(-1, D)
        k_o_2d = k_o.view(-1, D)
        
        N_q = q_2d.shape[0]
        N_k = k_2d.shape[0]
        
        # Grid size covers both Q and K
        total_rows = N_q + N_k
        BLOCK_SIZE = triton.next_power_of_2(D)
        
        # Launch fused kernel
        _fused_rmsnorm_kernel[(total_rows,)](
            q_2d, k_2d, norm_weight,
            q_o_2d, k_o_2d,
            q_2d.stride(0), q_2d.stride(1),
            k_2d.stride(0), k_2d.stride(1),
            q_o_2d.stride(0), q_o_2d.stride(1),
            k_o_2d.stride(0), k_o_2d.stride(1),
            norm_weight.stride(0),
            N_q, N_k, D,
            eps,
            BLOCK_SIZE=BLOCK_SIZE
        )
        return q_o, k_o
        
    except (RuntimeError, ValueError):
        # Fallback for complex non-contiguous layouts where view(-1, D) fails
        # Use flashinfer directly (baseline behavior)
        # We re-use the allocated outputs
        flashinfer.norm.rmsnorm(q, norm_weight, 1e-6, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, 1e-6, out=k_o)
        return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}