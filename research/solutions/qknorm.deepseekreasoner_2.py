import torch
import flashinfer
import triton
import triton.language as tl

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Fast path: both tensors are already contiguous in the last dimension
    # which is common in weight-QKV fusion scenarios
    if q.stride(-1) == 1 and k.stride(-1) == 1:
        # Use 2D view without copying
        q_2d = q.view(-1, q.size(-1))
        k_2d = k.view(-1, k.size(-1))
        
        # Direct rmsnorm calls without extra allocations
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
        
        return q_o.view(q.shape), k_o.view(k.shape)
    
    # Slow path: handle non-contiguous inputs via vectorized Triton kernel
    return _fused_qknorm_triton(q, k, norm_weight)

@triton.jit
def _rmsnorm_fwd_kernel(
    x_ptr, norm_weight_ptr, y_ptr,
    stride_x_batch, stride_x_hidden,
    stride_y_batch, stride_y_hidden,
    hidden_size: tl.constexpr,
    eps: tl.constexpr = 1e-5,
    BLOCK_SIZE: tl.constexpr = 1024,
):
    pid = tl.program_id(0)
    off_batch = pid
    offs = tl.arange(0, BLOCK_SIZE)
    
    # Load x values
    x_ptrs = x_ptr + off_batch * stride_x_batch + offs * stride_x_hidden
    mask = offs < hidden_size
    x = tl.load(x_ptrs, mask=mask, other=0.0)
    
    # Compute RMS
    x_f32 = x.to(tl.float32)
    rms = tl.sqrt(tl.sum(x_f32 * x_f32) / hidden_size + eps)
    rms = 1.0 / rms
    
    # Load weight values
    w_ptrs = norm_weight_ptr + offs * 1
    w = tl.load(w_ptrs, mask=mask, other=1.0)
    
    # Normalize and scale
    y = (x * rms) * w
    
    # Store results
    y_ptrs = y_ptr + off_batch * stride_y_batch + offs * stride_y_hidden
    tl.store(y_ptrs, y, mask=mask)

def _fused_qknorm_triton(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    hidden_size = q.size(-1)
    batch_size = q.numel() // hidden_size
    
    # Output tensors with correct strides
    q_o = torch.empty_strided(
        q.shape,
        q.stride(),
        device=q.device,
        dtype=q.dtype
    )
    k_o = torch.empty_strided(
        k.shape,
        k.stride(),
        device=k.device,
        dtype=k.dtype
    )
    
    # Flatten to 2D view while preserving strides
    q_2d = q.view(batch_size, hidden_size)
    k_2d = k.view(batch_size, hidden_size)
    q_o_2d = q_o.view(batch_size, hidden_size)
    k_o_2d = k_o.view(batch_size, hidden_size)
    
    # Choose block size based on hidden size
    block_size = min(1024, triton.next_power_of_2(hidden_size))
    
    # Launch kernels
    grid = (batch_size,)
    _rmsnorm_fwd_kernel[grid](
        q_2d, norm_weight, q_o_2d,
        q_2d.stride(0), q_2d.stride(1),
        q_o_2d.stride(0), q_o_2d.stride(1),
        hidden_size,
        BLOCK_SIZE=block_size,
    )
    
    _rmsnorm_fwd_kernel[grid](
        k_2d, norm_weight, k_o_2d,
        k_2d.stride(0), k_2d.stride(1),
        k_o_2d.stride(0), k_o_2d.stride(1),
        hidden_size,
        BLOCK_SIZE=block_size,
    )
    
    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer
import triton
import triton.language as tl

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Fast path: both tensors are already contiguous in the last dimension
    # which is common in weight-QKV fusion scenarios
    if q.stride(-1) == 1 and k.stride(-1) == 1:
        # Use 2D view without copying
        q_2d = q.view(-1, q.size(-1))
        k_2d = k.view(-1, k.size(-1))
        
        # Direct rmsnorm calls without extra allocations
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
        
        return q_o.view(q.shape), k_o.view(k.shape)
    
    # Slow path: handle non-contiguous inputs via vectorized Triton kernel
    return _fused_qknorm_triton(q, k, norm_weight)

@triton.jit
def _rmsnorm_fwd_kernel(
    x_ptr, norm_weight_ptr, y_ptr,
    stride_x_batch, stride_x_hidden,
    stride_y_batch, stride_y_hidden,
    hidden_size: tl.constexpr,
    eps: tl.constexpr = 1e-5,
    BLOCK_SIZE: tl.constexpr = 1024,
):
    pid = tl.program_id(0)
    off_batch = pid
    offs = tl.arange(0, BLOCK_SIZE)
    
    # Load x values
    x_ptrs = x_ptr + off_batch * stride_x_batch + offs * stride_x_hidden
    mask = offs < hidden_size
    x = tl.load(x_ptrs, mask=mask, other=0.0)
    
    # Compute RMS
    x_f32 = x.to(tl.float32)
    rms = tl.sqrt(tl.sum(x_f32 * x_f32) / hidden_size + eps)
    rms = 1.0 / rms
    
    # Load weight values
    w_ptrs = norm_weight_ptr + offs * 1
    w = tl.load(w_ptrs, mask=mask, other=1.0)
    
    # Normalize and scale
    y = (x * rms) * w
    
    # Store results
    y_ptrs = y_ptr + off_batch * stride_y_batch + offs * stride_y_hidden
    tl.store(y_ptrs, y, mask=mask)

def _fused_qknorm_triton(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    hidden_size = q.size(-1)
    batch_size = q.numel() // hidden_size
    
    # Output tensors with correct strides
    q_o = torch.empty_strided(
        q.shape,
        q.stride(),
        device=q.device,
        dtype=q.dtype
    )
    k_o = torch.empty_strided(
        k.shape,
        k.stride(),
        device=k.device,
        dtype=k.dtype
    )
    
    # Flatten to 2D view while preserving strides
    q_2d = q.view(batch_size, hidden_size)
    k_2d = k.view(batch_size, hidden_size)
    q_o_2d = q_o.view(batch_size, hidden_size)
    k_o_2d = k_o.view(batch_size, hidden_size)
    
    # Choose block size based on hidden size
    block_size = min(1024, triton.next_power_of_2(hidden_size))
    
    # Launch kernels
    grid = (batch_size,)
    _rmsnorm_fwd_kernel[grid](
        q_2d, norm_weight, q_o_2d,
        q_2d.stride(0), q_2d.stride(1),
        q_o_2d.stride(0), q_o_2d.stride(1),
        hidden_size,
        BLOCK_SIZE=block_size,
    )
    
    _rmsnorm_fwd_kernel[grid](
        k_2d, norm_weight, k_o_2d,
        k_2d.stride(0), k_2d.stride(1),
        k_o_2d.stride(0), k_o_2d.stride(1),
        hidden_size,
        BLOCK_SIZE=block_size,
    )
    
    return q_o, k_o
"""
        return {"code": code}
