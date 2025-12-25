import torch
import flashinfer
import triton
import triton.language as tl
from typing import Tuple

@triton.jit
def _qknorm_kernel(
    q_ptr, k_ptr, norm_weight_ptr, q_out_ptr, k_out_ptr,
    q_stride_batch, q_stride_head, q_stride_seq, q_stride_feat,
    k_stride_batch, k_stride_head, k_stride_seq, k_stride_feat,
    hidden_dim, eps, BLOCK_SIZE: tl.constexpr,
    QKV_SEPARATE: tl.constexpr,
    HAS_BATCH: tl.constexpr, HAS_HEAD: tl.constexpr,
    q_is_contiguous: tl.constexpr, k_is_contiguous: tl.constexpr
):
    pid = tl.program_id(0)
    
    if QKV_SEPARATE:
        off_features = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
        off_features_mask = off_features < hidden_dim
        
        weight = tl.load(norm_weight_ptr + off_features, mask=off_features_mask)
        
        q_rs_sum = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
        k_rs_sum = tl.zeros([BLOCK_SIZE], dtype=tl.float32)
        
        if HAS_BATCH and HAS_HEAD:
            batch_size = tl.num_program_ids(1)
            head_size = tl.num_program_ids(2)
            batch_idx = tl.program_id(1)
            head_idx = tl.program_id(2)
            
            for seq_idx in range(tl.num_program_ids(3)):
                q_offset = batch_idx * q_stride_batch + head_idx * q_stride_head + seq_idx * q_stride_seq
                k_offset = batch_idx * k_stride_batch + head_idx * k_stride_head + seq_idx * k_stride_seq
                
                q_val = tl.load(q_ptr + q_offset + off_features, mask=off_features_mask, other=0.0)
                k_val = tl.load(k_ptr + k_offset + off_features, mask=off_features_mask, other=0.0)
                
                q_rs_sum += q_val * q_val
                k_rs_sum += k_val * k_val
                
                q_norm = q_val * tl.rsqrt(q_rs_sum / (seq_idx + 1) + eps) * weight
                k_norm = k_val * tl.rsqrt(k_rs_sum / (seq_idx + 1) + eps) * weight
                
                tl.store(q_out_ptr + q_offset + off_features, q_norm, mask=off_features_mask)
                tl.store(k_out_ptr + k_offset + off_features, k_norm, mask=off_features_mask)
        else:
            total_elements = tl.num_program_ids(1)
            elem_idx = tl.program_id(1)
            
            if q_is_contiguous and k_is_contiguous:
                q_offset = elem_idx * hidden_dim
                k_offset = elem_idx * hidden_dim
            else:
                q_offset = elem_idx * q_stride_seq
                k_offset = elem_idx * k_stride_seq
            
            q_val = tl.load(q_ptr + q_offset + off_features, mask=off_features_mask, other=0.0)
            k_val = tl.load(k_ptr + k_offset + off_features, mask=off_features_mask, other=0.0)
            
            q_norm = q_val * tl.rsqrt(tl.sum(q_val * q_val) / hidden_dim + eps) * weight
            k_norm = k_val * tl.rsqrt(tl.sum(k_val * k_val) / hidden_dim + eps) * weight
            
            tl.store(q_out_ptr + q_offset + off_features, q_norm, mask=off_features_mask)
            tl.store(k_out_ptr + k_offset + off_features, k_norm, mask=off_features_mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor, eps: float = 1e-6):
    device = q.device
    dtype = q.dtype
    
    if q.dim() == 2:
        q_2d = q
        k_2d = k
        q_out = torch.empty_like(q_2d)
        k_out = torch.empty_like(k_2d)
        
        n_elements = q_2d.shape[0]
        hidden_dim = q_2d.shape[1]
        
        BLOCK_SIZE = 128 if hidden_dim % 128 == 0 else 64
        
        grid = (triton.cdiv(hidden_dim, BLOCK_SIZE), n_elements)
        
        q_is_contiguous = q_2d.is_contiguous()
        k_is_contiguous = k_2d.is_contiguous()
        
        _qknorm_kernel[grid](
            q_2d, k_2d, norm_weight, q_out, k_out,
            0, 0, q_2d.stride(0), q_2d.stride(1),
            0, 0, k_2d.stride(0), k_2d.stride(1),
            hidden_dim, eps, BLOCK_SIZE,
            True, False, False, q_is_contiguous, k_is_contiguous
        )
        
        return q_out.view(q.shape), k_out.view(k.shape)
    
    elif q.dim() == 4:
        batch_size, num_heads, seq_len, hidden_dim = q.shape
        
        q_out = torch.empty_like(q)
        k_out = torch.empty_like(k)
        
        BLOCK_SIZE = 128 if hidden_dim % 128 == 0 else 64
        
        grid = (
            triton.cdiv(hidden_dim, BLOCK_SIZE),
            batch_size,
            num_heads,
            seq_len
        )
        
        _qknorm_kernel[grid](
            q, k, norm_weight, q_out, k_out,
            q.stride(0), q.stride(1), q.stride(2), q.stride(3),
            k.stride(0), k.stride(1), k.stride(2), k.stride(3),
            hidden_dim, eps, BLOCK_SIZE,
            False, True, True, True, True
        )
        
        return q_out, k_out
    
    else:
        q_2d = q.reshape(-1, q.shape[-1])
        k_2d = k.reshape(-1, k.shape[-1])
        q_out = torch.empty_like(q_2d)
        k_out = torch.empty_like(k_2d)
        
        n_elements = q_2d.shape[0]
        hidden_dim = q_2d.shape[1]
        
        BLOCK_SIZE = 128 if hidden_dim % 128 == 0 else 64
        
        grid = (triton.cdiv(hidden_dim, BLOCK_SIZE), n_elements)
        
        q_is_contiguous = q_2d.is_contiguous()
        k_is_contiguous = k_2d.is_contiguous()
        
        _qknorm_kernel[grid](
            q_2d, k_2d, norm_weight, q_out, k_out,
            0, 0, q_2d.stride(0), q_2d.stride(1),
            0, 0, k_2d.stride(0), k_2d.stride(1),
            hidden_dim, eps, BLOCK_SIZE,
            True, False, False, q_is_contiguous, k_is_contiguous
        )
        
        return q_out.view(q.shape), k_out.view(k.shape)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import flashinfer
import triton
import triton.language as tl
from typing import Tuple

@triton.jit
def _qknorm_kernel(
    q_ptr, k_ptr, norm_weight_ptr, q_out_ptr, k_out_ptr,
    q_stride_batch, q_stride_head, q_stride_seq, q_stride_feat,
    k_stride_batch, k_stride_head, k_stride_seq, k_stride_feat,
    hidden_dim, eps, BLOCK_SIZE: tl.constexpr,
    QKV_SEPARATE: tl.constexpr,
    HAS_BATCH: tl.constexpr, HAS_HEAD: tl.constexpr,
    q_is_contiguous: tl.constexpr, k_is_contiguous: tl.constexpr
):
    pid = tl.program_id(0)
    
    if QKV_SEPARATE:
        off_features = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
        off_features_mask = off_features < hidden_dim
        
        weight = tl.load(norm_weight_ptr + off_features, mask=off_features_mask)
        
        if HAS_BATCH and HAS_HEAD:
            batch_size = tl.num_program_ids(1)
            head_size = tl.num_program_ids(2)
            batch_idx = tl.program_id(1)
            head_idx = tl.program_id(2)
            
            for seq_idx in range(tl.num_program_ids(3)):
                q_offset = batch_idx * q_stride_batch + head_idx * q_stride_head + seq_idx * q_stride_seq
                k_offset = batch_idx * k_stride_batch + head_idx * k_stride_head + seq_idx * k_stride_seq
                
                q_val = tl.load(q_ptr + q_offset + off_features, mask=off_features_mask, other=0.0)
                k_val = tl.load(k_ptr + k_offset + off_features, mask=off_features_mask, other=0.0)
                
                q_var = tl.sum(q_val * q_val) / hidden_dim
                k_var = tl.sum(k_val * k_val) / hidden_dim
                
                q_norm = q_val * tl.rsqrt(q_var + eps) * weight
                k_norm = k_val * tl.rsqrt(k_var + eps) * weight
                
                tl.store(q_out_ptr + q_offset + off_features, q_norm, mask=off_features_mask)
                tl.store(k_out_ptr + k_offset + off_features, k_norm, mask=off_features_mask)
        else:
            total_elements = tl.num_program_ids(1)
            elem_idx = tl.program_id(1)
            
            if q_is_contiguous and k_is_contiguous:
                q_offset = elem_idx * hidden_dim
                k_offset = elem_idx * hidden_dim
            else:
                q_offset = elem_idx * q_stride_seq
                k_offset = elem_idx * k_stride_seq
            
            q_val = tl.load(q_ptr + q_offset + off_features, mask=off_features_mask, other=0.0)
            k_val = tl.load(k_ptr + k_offset + off_features, mask=off_features_mask, other=0.0)
            
            q_var = tl.sum(q_val * q_val) / hidden_dim
            k_var = tl.sum(k_val * k_val) / hidden_dim
            
            q_norm = q_val * tl.rsqrt(q_var + eps) * weight
            k_norm = k_val * tl.rsqrt(k_var + eps) * weight
            
            tl.store(q_out_ptr + q_offset + off_features, q_norm, mask=off_features_mask)
            tl.store(k_out_ptr + k_offset + off_features, k_norm, mask=off_features_mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor, eps: float = 1e-6):
    device = q.device
    dtype = q.dtype
    
    if q.dim() == 2:
        q_2d = q
        k_2d = k
        q_out = torch.empty_like(q_2d)
        k_out = torch.empty_like(k_2d)
        
        n_elements = q_2d.shape[0]
        hidden_dim = q_2d.shape[1]
        
        BLOCK_SIZE = 128 if hidden_dim % 128 == 0 else 64
        
        grid = (triton.cdiv(hidden_dim, BLOCK_SIZE), n_elements)
        
        q_is_contiguous = q_2d.is_contiguous()
        k_is_contiguous = k_2d.is_contiguous()
        
        _qknorm_kernel[grid](
            q_2d, k_2d, norm_weight, q_out, k_out,
            0, 0, q_2d.stride(0), q_2d.stride(1),
            0, 0, k_2d.stride(0), k_2d.stride(1),
            hidden_dim, eps, BLOCK_SIZE,
            True, False, False, q_is_contiguous, k_is_contiguous
        )
        
        return q_out.view(q.shape), k_out.view(k.shape)
    
    elif q.dim() == 4:
        batch_size, num_heads, seq_len, hidden_dim = q.shape
        
        q_out = torch.empty_like(q)
        k_out = torch.empty_like(k)
        
        BLOCK_SIZE = 128 if hidden_dim % 128 == 0 else 64
        
        grid = (
            triton.cdiv(hidden_dim, BLOCK_SIZE),
            batch_size,
            num_heads,
            seq_len
        )
        
        _qknorm_kernel[grid](
            q, k, norm_weight, q_out, k_out,
            q.stride(0), q.stride(1), q.stride(2), q.stride(3),
            k.stride(0), k.stride(1), k.stride(2), k.stride(3),
            hidden_dim, eps, BLOCK_SIZE,
            False, True, True, True, True
        )
        
        return q_out, k_out
    
    else:
        original_q_shape = q.shape
        original_k_shape = k.shape
        
        q_2d = q.view(-1, q.shape[-1])
        k_2d = k.view(-1, k.shape[-1])
        q_out = torch.empty_like(q_2d)
        k_out = torch.empty_like(k_2d)
        
        n_elements = q_2d.shape[0]
        hidden_dim = q_2d.shape[1]
        
        BLOCK_SIZE = 128 if hidden_dim % 128 == 0 else 64
        
        grid = (triton.cdiv(hidden_dim, BLOCK_SIZE), n_elements)
        
        q_is_contiguous = q_2d.is_contiguous()
        k_is_contiguous = k_2d.is_contiguous()
        
        _qknorm_kernel[grid](
            q_2d, k_2d, norm_weight, q_out, k_out,
            0, 0, q_2d.stride(0), q_2d.stride(1),
            0, 0, k_2d.stride(0), k_2d.stride(1),
            hidden_dim, eps, BLOCK_SIZE,
            True, False, False, q_is_contiguous, k_is_contiguous
        )
        
        return q_out.view(original_q_shape), k_out.view(original_k_shape)

"""}
