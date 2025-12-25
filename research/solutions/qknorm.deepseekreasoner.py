import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_kernel(
    q_ptr, k_ptr, weight_ptr, out_q_ptr, out_k_ptr,
    stride_q0, stride_q1, stride_q2, stride_q3,
    stride_k0, stride_k1, stride_k2, stride_k3,
    stride_out_q0, stride_out_q1, stride_out_q2, stride_out_q3,
    stride_out_k0, stride_out_k1, stride_out_k2, stride_out_k3,
    hidden_dim, eps, BLOCK_SIZE: tl.constexpr,
    qkv_order: tl.constexpr
):
    pid = tl.program_id(0)
    num_rows = hidden_dim
    
    offset = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offset < num_rows
    
    weight = tl.load(weight_ptr + offset, mask=mask, other=0.0)
    
    q_offset = offset
    k_offset = offset
    
    if qkv_order == 0:
        q_row = tl.load(q_ptr + q_offset, mask=mask, other=0.0)
        k_row = tl.load(k_ptr + k_offset, mask=mask, other=0.0)
    else:
        q_row = tl.load(q_ptr + q_offset * stride_q3, mask=mask, other=0.0)
        k_row = tl.load(k_ptr + k_offset * stride_k3, mask=mask, other=0.0)
    
    q_square_sum = tl.sum(q_row * q_row)
    k_square_sum = tl.sum(k_row * k_row)
    
    q_scale = tl.sqrt(q_square_sum / hidden_dim + eps)
    k_scale = tl.sqrt(k_square_sum / hidden_dim + eps)
    
    q_norm = q_row / q_scale
    k_norm = k_row / k_scale
    
    q_out = q_norm * weight
    k_out = k_norm * weight
    
    if qkv_order == 0:
        tl.store(out_q_ptr + offset, q_out, mask=mask)
        tl.store(out_k_ptr + offset, k_out, mask=mask)
    else:
        tl.store(out_q_ptr + offset * stride_out_q3, q_out, mask=mask)
        tl.store(out_k_ptr + offset * stride_out_k3, k_out, mask=mask)

def optimized_qknorm(q, k, norm_weight, eps=1e-6):
    assert q.dim() == k.dim(), "q and k must have same number of dimensions"
    assert q.shape[-1] == k.shape[-1] == norm_weight.shape[-1], "Last dimension mismatch"
    
    hidden_dim = q.shape[-1]
    original_shape = q.shape
    
    is_q_contiguous = q.is_contiguous()
    is_k_contiguous = k.is_contiguous()
    
    q_2d = q.view(-1, hidden_dim)
    k_2d = k.view(-1, hidden_dim)
    
    if is_q_contiguous and is_k_contiguous:
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        
        grid = (triton.cdiv(hidden_dim, 1024),)
        _qknorm_kernel[grid](
            q_2d, k_2d, norm_weight, q_o, k_o,
            0, 0, 0, 1, 0, 0, 0, 1,
            0, 0, 0, 1, 0, 0, 0, 1,
            hidden_dim, eps, 1024, 0
        )
    else:
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        
        q_stride = q.stride()
        k_stride = k.stride()
        q_o_stride = q_o.stride()
        k_o_stride = k_o.stride()
        
        batch_size = q_2d.shape[0]
        grid = (batch_size,)
        
        for i in range(batch_size):
            q_ptr = q[i].reshape(-1, hidden_dim)
            k_ptr = k[i].reshape(-1, hidden_dim)
            q_o_ptr = q_o[i].reshape(-1, hidden_dim)
            k_o_ptr = k_o[i].reshape(-1, hidden_dim)
            
            _qknorm_kernel[grid](
                q_ptr, k_ptr, norm_weight, q_o_ptr, k_o_ptr,
                q_stride[0], q_stride[1], q_stride[2], q_stride[3],
                k_stride[0], k_stride[1], k_stride[2], k_stride[3],
                q_o_stride[0], q_o_stride[1], q_o_stride[2], q_o_stride[3],
                k_o_stride[0], k_o_stride[1], k_o_stride[2], k_o_stride[3],
                hidden_dim, eps, 1024, 1
            )
    
    return q_o.view(original_shape), k_o.view(k.shape)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    return optimized_qknorm(q, k, norm_weight)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_kernel(
    q_ptr, k_ptr, weight_ptr, out_q_ptr, out_k_ptr,
    stride_q0, stride_q1, stride_q2, stride_q3,
    stride_k0, stride_k1, stride_k2, stride_k3,
    stride_out_q0, stride_out_q1, stride_out_q2, stride_out_q3,
    stride_out_k0, stride_out_k1, stride_out_k2, stride_out_k3,
    hidden_dim, eps, BLOCK_SIZE: tl.constexpr,
    qkv_order: tl.constexpr
):
    pid = tl.program_id(0)
    num_rows = hidden_dim
    
    offset = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offset < num_rows
    
    weight = tl.load(weight_ptr + offset, mask=mask, other=0.0)
    
    q_offset = offset
    k_offset = offset
    
    if qkv_order == 0:
        q_row = tl.load(q_ptr + q_offset, mask=mask, other=0.0)
        k_row = tl.load(k_ptr + k_offset, mask=mask, other=0.0)
    else:
        q_row = tl.load(q_ptr + q_offset * stride_q3, mask=mask, other=0.0)
        k_row = tl.load(k_ptr + k_offset * stride_k3, mask=mask, other=0.0)
    
    q_square_sum = tl.sum(q_row * q_row)
    k_square_sum = tl.sum(k_row * k_row)
    
    q_scale = tl.sqrt(q_square_sum / hidden_dim + eps)
    k_scale = tl.sqrt(k_square_sum / hidden_dim + eps)
    
    q_norm = q_row / q_scale
    k_norm = k_row / k_scale
    
    q_out = q_norm * weight
    k_out = k_norm * weight
    
    if qkv_order == 0:
        tl.store(out_q_ptr + offset, q_out, mask=mask)
        tl.store(out_k_ptr + offset, k_out, mask=mask)
    else:
        tl.store(out_q_ptr + offset * stride_out_q3, q_out, mask=mask)
        tl.store(out_k_ptr + offset * stride_out_k3, k_out, mask=mask)

def optimized_qknorm(q, k, norm_weight, eps=1e-6):
    assert q.dim() == k.dim(), "q and k must have same number of dimensions"
    assert q.shape[-1] == k.shape[-1] == norm_weight.shape[-1], "Last dimension mismatch"
    
    hidden_dim = q.shape[-1]
    original_shape = q.shape
    
    is_q_contiguous = q.is_contiguous()
    is_k_contiguous = k.is_contiguous()
    
    q_2d = q.view(-1, hidden_dim)
    k_2d = k.view(-1, hidden_dim)
    
    if is_q_contiguous and is_k_contiguous:
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        
        grid = (triton.cdiv(hidden_dim, 1024),)
        _qknorm_kernel[grid](
            q_2d, k_2d, norm_weight, q_o, k_o,
            0, 0, 0, 1, 0, 0, 0, 1,
            0, 0, 0, 1, 0, 0, 0, 1,
            hidden_dim, eps, 1024, 0
        )
    else:
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        
        q_stride = q.stride()
        k_stride = k.stride()
        q_o_stride = q_o.stride()
        k_o_stride = k_o.stride()
        
        batch_size = q_2d.shape[0]
        grid = (batch_size,)
        
        for i in range(batch_size):
            q_ptr = q[i].reshape(-1, hidden_dim)
            k_ptr = k[i].reshape(-1, hidden_dim)
            q_o_ptr = q_o[i].reshape(-1, hidden_dim)
            k_o_ptr = k_o[i].reshape(-1, hidden_dim)
            
            _qknorm_kernel[grid](
                q_ptr, k_ptr, norm_weight, q_o_ptr, k_o_ptr,
                q_stride[0], q_stride[1], q_stride[2], q_stride[3],
                k_stride[0], k_stride[1], k_stride[2], k_stride[3],
                q_o_stride[0], q_o_stride[1], q_o_stride[2], q_o_stride[3],
                k_o_stride[0], k_o_stride[1], k_o_stride[2], k_o_stride[3],
                hidden_dim, eps, 1024, 1
            )
    
    return q_o.view(original_shape), k_o.view(k.shape)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    return optimized_qknorm(q, k, norm_weight)
'''
        return {"code": code}
