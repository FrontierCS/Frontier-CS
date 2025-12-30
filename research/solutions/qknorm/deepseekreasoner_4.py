import torch
import flashinfer
import triton
import triton.language as tl
from typing import Tuple

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
    ],
    key=['hidden_dim']
)
@triton.jit
def _rmsnorm_kernel(
    x_ptr,
    weight_ptr,
    out_ptr,
    x_stride_batch,
    x_stride_row,
    x_stride_col,
    out_stride_batch,
    out_stride_row,
    out_stride_col,
    eps: tl.constexpr,
    hidden_dim: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
):
    row_idx = tl.program_id(0)
    batch_idx = tl.program_id(1)
    
    x_row_ptr = x_ptr + batch_idx * x_stride_batch + row_idx * x_stride_row
    out_row_ptr = out_ptr + batch_idx * out_stride_batch + row_idx * out_stride_row
    
    mean_square = tl.zeros([1], tl.float32)
    
    for offset in range(0, hidden_dim, BLOCK_SIZE):
        col = offset + tl.arange(0, BLOCK_SIZE)
        mask = col < hidden_dim
        
        x_val = tl.load(x_row_ptr + col * x_stride_col, mask=mask, other=0.0).to(tl.float32)
        mean_square += tl.sum(x_val * x_val, axis=0)
    
    rms = tl.sqrt(mean_square / hidden_dim + eps)
    
    for offset in range(0, hidden_dim, BLOCK_SIZE):
        col = offset + tl.arange(0, BLOCK_SIZE)
        mask = col < hidden_dim
        
        x_val = tl.load(x_row_ptr + col * x_stride_col, mask=mask, other=0.0)
        weight_val = tl.load(weight_ptr + col, mask=mask, other=1.0)
        
        normalized = (x_val.to(tl.float32) / rms).to(x_val.dtype)
        out_val = normalized * weight_val
        
        tl.store(out_row_ptr + col * out_stride_col, out_val, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    if q.dim() != 2 or k.dim() != 2:
        q_2d = q.reshape(-1, q.shape[-1])
        k_2d = k.reshape(-1, k.shape[-1])
        
        q_out = torch.empty_like(q_2d)
        k_out = torch.empty_like(k_2d)
        
        n_rows_q = q_2d.shape[0]
        n_rows_k = k_2d.shape[0]
        hidden_dim = q_2d.shape[-1]
        
        grid_q = lambda meta: (n_rows_q, 1)
        grid_k = lambda meta: (n_rows_k, 1)
        
        q_is_contiguous = q_2d.is_contiguous()
        k_is_contiguous = k_2d.is_contiguous()
        
        if q_is_contiguous and k_is_contiguous:
            q_strides = (q_2d.stride(0), q_2d.stride(0), q_2d.stride(1))
            k_strides = (k_2d.stride(0), k_2d.stride(0), k_2d.stride(1))
        else:
            q_strides = (q_2d.stride(-2) if q_2d.dim() >= 2 else 0, 
                        q_2d.stride(-2) if q_2d.dim() >= 2 else 0,
                        q_2d.stride(-1))
            k_strides = (k_2d.stride(-2) if k_2d.dim() >= 2 else 0,
                        k_2d.stride(-2) if k_2d.dim() >= 2 else 0,
                        k_2d.stride(-1))
        
        out_strides = (q_out.stride(0), q_out.stride(0), q_out.stride(1))
        
        _rmsnorm_kernel[grid_q](
            q_2d, norm_weight, q_out,
            q_strides[0], q_strides[1], q_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        _rmsnorm_kernel[grid_k](
            k_2d, norm_weight, k_out,
            k_strides[0], k_strides[1], k_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        return q_out.view(q.shape), k_out.view(k.shape)
    else:
        q_out = torch.empty_like(q)
        k_out = torch.empty_like(k)
        
        n_rows_q = q.shape[0]
        n_rows_k = k.shape[0]
        hidden_dim = q.shape[-1]
        
        grid_q = lambda meta: (n_rows_q, 1)
        grid_k = lambda meta: (n_rows_k, 1)
        
        q_strides = (q.stride(0), q.stride(0), q.stride(1))
        k_strides = (k.stride(0), k.stride(0), k.stride(1))
        out_strides = (q_out.stride(0), q_out.stride(0), q_out.stride(1))
        
        _rmsnorm_kernel[grid_q](
            q, norm_weight, q_out,
            q_strides[0], q_strides[1], q_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        _rmsnorm_kernel[grid_k](
            k, norm_weight, k_out,
            k_strides[0], k_strides[1], k_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        return q_out, k_out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import flashinfer
import triton
import triton.language as tl
from typing import Tuple

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
    ],
    key=['hidden_dim']
)
@triton.jit
def _rmsnorm_kernel(
    x_ptr,
    weight_ptr,
    out_ptr,
    x_stride_batch,
    x_stride_row,
    x_stride_col,
    out_stride_batch,
    out_stride_row,
    out_stride_col,
    eps: tl.constexpr,
    hidden_dim: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
):
    row_idx = tl.program_id(0)
    batch_idx = tl.program_id(1)
    
    x_row_ptr = x_ptr + batch_idx * x_stride_batch + row_idx * x_stride_row
    out_row_ptr = out_ptr + batch_idx * out_stride_batch + row_idx * out_stride_row
    
    mean_square = tl.zeros([1], tl.float32)
    
    for offset in range(0, hidden_dim, BLOCK_SIZE):
        col = offset + tl.arange(0, BLOCK_SIZE)
        mask = col < hidden_dim
        
        x_val = tl.load(x_row_ptr + col * x_stride_col, mask=mask, other=0.0).to(tl.float32)
        mean_square += tl.sum(x_val * x_val, axis=0)
    
    rms = tl.sqrt(mean_square / hidden_dim + eps)
    
    for offset in range(0, hidden_dim, BLOCK_SIZE):
        col = offset + tl.arange(0, BLOCK_SIZE)
        mask = col < hidden_dim
        
        x_val = tl.load(x_row_ptr + col * x_stride_col, mask=mask, other=0.0)
        weight_val = tl.load(weight_ptr + col, mask=mask, other=1.0)
        
        normalized = (x_val.to(tl.float32) / rms).to(x_val.dtype)
        out_val = normalized * weight_val
        
        tl.store(out_row_ptr + col * out_stride_col, out_val, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    if q.dim() != 2 or k.dim() != 2:
        q_2d = q.reshape(-1, q.shape[-1])
        k_2d = k.reshape(-1, k.shape[-1])
        
        q_out = torch.empty_like(q_2d)
        k_out = torch.empty_like(k_2d)
        
        n_rows_q = q_2d.shape[0]
        n_rows_k = k_2d.shape[0]
        hidden_dim = q_2d.shape[-1]
        
        grid_q = lambda meta: (n_rows_q, 1)
        grid_k = lambda meta: (n_rows_k, 1)
        
        q_is_contiguous = q_2d.is_contiguous()
        k_is_contiguous = k_2d.is_contiguous()
        
        if q_is_contiguous and k_is_contiguous:
            q_strides = (q_2d.stride(0), q_2d.stride(0), q_2d.stride(1))
            k_strides = (k_2d.stride(0), k_2d.stride(0), k_2d.stride(1))
        else:
            q_strides = (q_2d.stride(-2) if q_2d.dim() >= 2 else 0, 
                        q_2d.stride(-2) if q_2d.dim() >= 2 else 0,
                        q_2d.stride(-1))
            k_strides = (k_2d.stride(-2) if k_2d.dim() >= 2 else 0,
                        k_2d.stride(-2) if k_2d.dim() >= 2 else 0,
                        k_2d.stride(-1))
        
        out_strides = (q_out.stride(0), q_out.stride(0), q_out.stride(1))
        
        _rmsnorm_kernel[grid_q](
            q_2d, norm_weight, q_out,
            q_strides[0], q_strides[1], q_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        _rmsnorm_kernel[grid_k](
            k_2d, norm_weight, k_out,
            k_strides[0], k_strides[1], k_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        return q_out.view(q.shape), k_out.view(k.shape)
    else:
        q_out = torch.empty_like(q)
        k_out = torch.empty_like(k)
        
        n_rows_q = q.shape[0]
        n_rows_k = k.shape[0]
        hidden_dim = q.shape[-1]
        
        grid_q = lambda meta: (n_rows_q, 1)
        grid_k = lambda meta: (n_rows_k, 1)
        
        q_strides = (q.stride(0), q.stride(0), q.stride(1))
        k_strides = (k.stride(0), k.stride(0), k.stride(1))
        out_strides = (q_out.stride(0), q_out.stride(0), q_out.stride(1))
        
        _rmsnorm_kernel[grid_q](
            q, norm_weight, q_out,
            q_strides[0], q_strides[1], q_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        _rmsnorm_kernel[grid_k](
            k, norm_weight, k_out,
            k_strides[0], k_strides[1], k_strides[2],
            out_strides[0], out_strides[1], out_strides[2],
            eps=1e-6,
            hidden_dim=hidden_dim
        )
        
        return q_out, k_out
'''
        return {"code": code}