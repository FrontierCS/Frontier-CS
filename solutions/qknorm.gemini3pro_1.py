import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_fused_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    stride_q_row, stride_k_row,
    stride_q_out, stride_k_out,
    N_q, N_k,
    H, eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Load Weights (once per block, broadcast to rows)
    off = tl.arange(0, BLOCK_SIZE)
    mask = off < H
    w = tl.load(W_ptr + off, mask=mask, other=0.0).to(tl.float32)
    
    # Determine if we are processing Q or K
    if pid < N_q:
        # Process Q
        row_idx = pid
        src_ptr = Q_ptr + row_idx * stride_q_row
        dst_ptr = Q_out_ptr + row_idx * stride_q_out
        
        # Load Data
        x = tl.load(src_ptr + off, mask=mask, other=0.0).to(tl.float32)
        
        # RMSNorm computation
        x_sq = x * x
        mean_sq = tl.sum(x_sq, axis=0) / H
        rstd = tl.rsqrt(mean_sq + eps)
        out = x * rstd * w
        
        # Store
        tl.store(dst_ptr + off, out, mask=mask)
        
    elif pid < N_q + N_k:
        # Process K
        row_idx = pid - N_q
        src_ptr = K_ptr + row_idx * stride_k_row
        dst_ptr = K_out_ptr + row_idx * stride_k_out
        
        # Load Data
        x = tl.load(src_ptr + off, mask=mask, other=0.0).to(tl.float32)
        
        # RMSNorm computation
        x_sq = x * x
        mean_sq = tl.sum(x_sq, axis=0) / H
        rstd = tl.rsqrt(mean_sq + eps)
        out = x * rstd * w
        
        # Store
        tl.store(dst_ptr + off, out, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Function to check layout and get flattening params without copy if possible
    def get_flatten_params(t):
        # Must be contiguous in the last dimension (HeadDim) for vectorization
        if t.stride(-1) != 1:
            t = t.contiguous()
        
        H = t.shape[-1]
        
        # Check if the tensor can be treated as a 2D matrix of (N, H)
        # where rows are separated by a constant stride.
        if t.dim() > 1:
            stride_row = t.stride(-2)
            # Check regularity of higher dimensions (batch/seq dims)
            # Logic: For the tensor to be viewable as (N, H) with stride_row,
            # higher dimensions must be flattened/merged correctly.
            # E.g. stride[i] == shape[i+1] * stride[i+1]
            is_regular = True
            for i in range(t.dim() - 3, -1, -1):
                if t.stride(i) != t.shape[i+1] * t.stride(i+1):
                    is_regular = False
                    break
            
            if is_regular:
                # Optimized path: Use strides directly (handles QKV fusion slice gaps)
                return t, t.numel() // H, stride_row
            else:
                # Fallback: Contiguous copy required due to complex layout
                t = t.contiguous()
                return t, t.numel() // H, H
        else:
            # 1D Tensor (H,)
            return t, 1, H

    q_in, N_q, stride_q = get_flatten_params(q)
    k_in, N_k, stride_k = get_flatten_params(k)

    # Allocate outputs
    # Using torch.empty creates contiguous tensors, which is efficient
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    H = norm_weight.shape[0]
    
    # Kernel Launch Configuration
    # We fuse Q and K processing into a single grid launch to reduce overhead
    grid = (N_q + N_k,)
    BLOCK_SIZE = triton.next_power_of_2(H)
    
    _qknorm_fused_kernel[grid](
        q_in, k_in, norm_weight,
        q_o, k_o,
        stride_q, stride_k,
        H, H, # Output strides are H (contiguous)
        N_q, N_k,
        H, 1e-6,
        BLOCK_SIZE=BLOCK_SIZE
    )
    
    return q_o, k_o

def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)
"""
        return {"code": code}
