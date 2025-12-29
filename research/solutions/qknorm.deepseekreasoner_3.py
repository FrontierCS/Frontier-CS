import torch
import flashinfer
import torch.utils.cpp_extension

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors with optimized handling of non-contiguous inputs.
    """
    # Save original shapes and strides
    q_shape = q.shape
    k_shape = k.shape
    
    # Get last dimension for normalization
    hidden_dim = q.shape[-1]
    
    # Reshape to 2D without forcing contiguous if possible
    # Use as_strided to handle non-contiguous tensors efficiently
    if q.is_contiguous():
        q_2d = q.view(-1, hidden_dim)
    else:
        # For non-contiguous q, create a view with proper strides
        num_elements = q.numel() // hidden_dim
        q_2d = torch.as_strided(q, (num_elements, hidden_dim), 
                               (q.stride()[-2] if q.dim() > 1 else hidden_dim, 1))
    
    if k.is_contiguous():
        k_2d = k.view(-1, hidden_dim)
    else:
        # For non-contiguous k, create a view with proper strides
        num_elements = k.numel() // hidden_dim
        k_2d = torch.as_strided(k, (num_elements, hidden_dim),
                               (k.stride()[-2] if k.dim() > 1 else hidden_dim, 1))
    
    # Create output tensors with optimal memory layout
    # Use empty_strided to preserve output layout matching input when possible
    if q.is_contiguous():
        q_out = torch.empty_like(q_2d)
    else:
        # For non-contiguous input, output will be contiguous for efficiency
        q_out = torch.empty((q_2d.size(0), hidden_dim), 
                           device=q.device, dtype=q.dtype)
    
    if k.is_contiguous():
        k_out = torch.empty_like(k_2d)
    else:
        k_out = torch.empty((k_2d.size(0), hidden_dim), 
                           device=k.device, dtype=k.dtype)
    
    # Apply normalization using flashinfer
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_out)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_out)
    
    # Reshape back to original shape
    return q_out.view(q_shape), k_out.view(k_shape)
'''
        return {"code": code}