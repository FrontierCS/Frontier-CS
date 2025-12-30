import torch
import triton
import triton.language as tl
import flashinfer
import sys
import os

@triton.jit
def _qknorm_fused_kernel(
    Q_ptr, Q_stride_blk, Q_vecs_per_blk, Q_n_blks,
    K_ptr, K_stride_blk, K_vecs_per_blk, K_n_blks,
    W_ptr,
    Q_out_ptr, K_out_ptr,
    Hidden_Dim, Eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Calculate Q total vectors
    Q_total_vecs = Q_n_blks * Q_vecs_per_blk
    
    if pid < Q_total_vecs:
        # Processing Q
        # Map linear vector index 'pid' to (block_index, vector_index_in_block)
        blk_id = pid // Q_vecs_per_blk
        vec_id = pid % Q_vecs_per_blk
        
        # Calculate Input Offset (Strided)
        # stride_blk is the stride between blocks in elements
        # vec_id * Hidden_Dim is the offset within the contiguous block
        in_offset = blk_id * Q_stride_blk + vec_id * Hidden_Dim
        
        # Calculate Output Offset (Dense/Contiguous)
        # We assume output is contiguous (N, D)
        out_offset = (blk_id * Q_vecs_per_blk + vec_id) * Hidden_Dim
        
        inp_ptr = Q_ptr + in_offset
        out_ptr = Q_out_ptr + out_offset
        
        # Load Weight
        cols = tl.arange(0, BLOCK_SIZE)
        mask = cols < Hidden_Dim
        
        w = tl.load(W_ptr + cols, mask=mask, other=0.0).to(tl.float32)
        x = tl.load(inp_ptr + cols, mask=mask, other=0.0).to(tl.float32)
        
        # RMSNorm Computation
        x_sq = x * x
        mean_sq = tl.sum(x_sq, axis=0) / Hidden_Dim
        inv_rms = tl.rsqrt(mean_sq + Eps)
        
        y = x * inv_rms * w
        
        tl.store(out_ptr + cols, y, mask=mask)

    elif pid < Q_total_vecs + (K_n_blks * K_vecs_per_blk):
        # Processing K
        k_pid = pid - Q_total_vecs
        blk_id = k_pid // K_vecs_per_blk
        vec_id = k_pid % K_vecs_per_blk
        
        in_offset = blk_id * K_stride_blk + vec_id * Hidden_Dim
        out_offset = (blk_id * K_vecs_per_blk + vec_id) * Hidden_Dim
        
        inp_ptr = K_ptr + in_offset
        out_ptr = K_out_ptr + out_offset
        
        cols = tl.arange(0, BLOCK_SIZE)
        mask = cols < Hidden_Dim
        
        w = tl.load(W_ptr + cols, mask=mask, other=0.0).to(tl.float32)
        x = tl.load(inp_ptr + cols, mask=mask, other=0.0).to(tl.float32)
        
        x_sq = x * x
        mean_sq = tl.sum(x_sq, axis=0) / Hidden_Dim
        inv_rms = tl.rsqrt(mean_sq + Eps)
        
        y = x * inv_rms * w
        
        tl.store(out_ptr + cols, y, mask=mask)

def _get_layout_params(t):
    """
    Analyzes tensor strides to handle QKV-sliced inputs efficiently.
    Returns (stride_blk, vecs_per_blk, num_blks) or None if copy is needed.
    """
    if t.numel() == 0:
        return 0, 0, 0
        
    ndim = t.dim()
    
    # Requirement 1: Last dimension must be contiguous (stride 1)
    # This is typical for HeadDim.
    if t.stride(-1) != 1:
        return None
        
    # Requirement 2: Find the largest contiguous inner block
    # Scan from -2 leftwards.
    vecs_per_blk = 1
    idx = -2
    
    while idx >= -ndim:
        # Check if dim `idx` is contiguous with `idx+1`
        if t.stride(idx) == t.shape[idx+1] * t.stride(idx+1):
            vecs_per_blk *= t.shape[idx]
            idx -= 1
        else:
            break
    
    # Requirement 3: Outer dimensions (0 to idx) must be linearizable
    # `idx` is the dimension where the gap occurs (or -ndim - 1 if fully contiguous)
    # Check if dimensions up to `idx` form a linear sequence of blocks.
    # Note: The stride of dimension `idx` determines the block stride.
    
    # We check stride consistency for dimensions 0 to idx-1.
    # If idx = -2, we check 0..(ndim-3).
    
    outer_limit = ndim + idx # converts negative idx to positive limit
    valid_outer = True
    
    for k in range(outer_limit):
        if t.stride(k) != t.shape[k+1] * t.stride(k+1):
            valid_outer = False
            break
            
    if not valid_outer:
        return None
        
    num_blks = 1
    for k in range(outer_limit + 1):
        num_blks *= t.shape[k]
        
    stride_blk = t.stride(idx)
    
    return stride_blk, vecs_per_blk, num_blks

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors efficiently using a fused Triton kernel.
    Handles non-contiguous inputs (like QKV slices) without unnecessary copies.
    """
    # Allocate dense output tensors
    q_out = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_out = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    # Analyze memory layout for Q
    q_params = _get_layout_params(q)
    if q_params is None:
        # Fallback: Create contiguous copy for reading, output is already dense
        # Treating as single block
        q_cont = q.contiguous()
        q_ptr = q_cont
        q_stride_blk = 0
        q_vecs_per_blk = q.numel() // q.shape[-1]
        q_n_blks = 1
    else:
        q_ptr = q
        q_stride_blk, q_vecs_per_blk, q_n_blks = q_params
        
    # Analyze memory layout for K
    k_params = _get_layout_params(k)
    if k_params is None:
        k_cont = k.contiguous()
        k_ptr = k_cont
        k_stride_blk = 0
        k_vecs_per_blk = k.numel() // k.shape[-1]
        k_n_blks = 1
    else:
        k_ptr = k
        k_stride_blk, k_vecs_per_blk, k_n_blks = k_params
        
    D = norm_weight.shape[0]
    total_vecs = q_n_blks * q_vecs_per_blk + k_n_blks * k_vecs_per_blk
    
    if total_vecs == 0:
        return q_out, k_out
        
    BLOCK_SIZE = triton.next_power_of_2(D)
    
    # Launch fused kernel
    grid = (total_vecs,)
    _qknorm_fused_kernel[grid](
        q_ptr, q_stride_blk, q_vecs_per_blk, q_n_blks,
        k_ptr, k_stride_blk, k_vecs_per_blk, k_n_blks,
        norm_weight,
        q_out, k_out,
        D, 1e-6,
        BLOCK_SIZE=BLOCK_SIZE
    )
    
    return q_out, k_out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}