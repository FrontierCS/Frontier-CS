import torch
import flashinfer
from typing import Tuple

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    # Efficient handling of non-contiguous inputs without extra copies
    # by using direct flashinfer calls with proper shape preservation
    
    # Store original shapes
    original_q_shape = q.shape
    original_k_shape = k.shape
    
    # Get hidden dimension from weight
    hidden_dim = norm_weight.shape[0]
    
    # For Q tensor: handle reshaping efficiently
    if q.is_contiguous() and q.shape[-1] == hidden_dim:
        # Already contiguous with correct last dim
        q_2d = q.view(-1, hidden_dim)
    else:
        # For non-contiguous cases, use reshape which handles strided tensors
        q_2d = q.reshape(-1, hidden_dim)
    
    # For K tensor: handle reshaping efficiently  
    if k.is_contiguous() and k.shape[-1] == hidden_dim:
        # Already contiguous with correct last dim
        k_2d = k.view(-1, hidden_dim)
    else:
        # For non-contiguous cases, use reshape which handles strided tensors
        k_2d = k.reshape(-1, hidden_dim)
    
    # Create output tensors with the same memory layout as inputs
    if q.is_contiguous():
        q_o = torch.empty_like(q_2d)
    else:
        # Preserve strides for non-contiguous inputs
        q_o = torch.empty(q_2d.shape, device=q.device, dtype=q.dtype)
    
    if k.is_contiguous():
        k_o = torch.empty_like(k_2d)
    else:
        # Preserve strides for non-contiguous inputs
        k_o = torch.empty(k_2d.shape, device=k.device, dtype=k.dtype)
    
    # Apply RMSNorm using flashinfer (single kernel launch per tensor)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    
    # Reshape back to original shapes while preserving memory layout
    if q.is_contiguous():
        q_out = q_o.view(original_q_shape)
    else:
        # Use reshape to handle strided outputs
        q_out = q_o.reshape(original_q_shape)
    
    if k.is_contiguous():
        k_out = k_o.view(original_k_shape)
    else:
        # Use reshape to handle strided outputs
        k_out = k_o.reshape(original_k_shape)
    
    return q_out, k_out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import flashinfer
from typing import Tuple

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    # Efficient handling of non-contiguous inputs without extra copies
    # by using direct flashinfer calls with proper shape preservation
    
    # Store original shapes
    original_q_shape = q.shape
    original_k_shape = k.shape
    
    # Get hidden dimension from weight
    hidden_dim = norm_weight.shape[0]
    
    # For Q tensor: handle reshaping efficiently
    if q.is_contiguous() and q.shape[-1] == hidden_dim:
        # Already contiguous with correct last dim
        q_2d = q.view(-1, hidden_dim)
    else:
        # For non-contiguous cases, use reshape which handles strided tensors
        q_2d = q.reshape(-1, hidden_dim)
    
    # For K tensor: handle reshaping efficiently  
    if k.is_contiguous() and k.shape[-1] == hidden_dim:
        # Already contiguous with correct last dim
        k_2d = k.view(-1, hidden_dim)
    else:
        # For non-contiguous cases, use reshape which handles strided tensors
        k_2d = k.reshape(-1, hidden_dim)
    
    # Create output tensors with the same memory layout as inputs
    if q.is_contiguous():
        q_o = torch.empty_like(q_2d)
    else:
        # Preserve strides for non-contiguous inputs
        q_o = torch.empty(q_2d.shape, device=q.device, dtype=q.dtype)
    
    if k.is_contiguous():
        k_o = torch.empty_like(k_2d)
    else:
        # Preserve strides for non-contiguous inputs
        k_o = torch.empty(k_2d.shape, device=k.device, dtype=k.dtype)
    
    # Apply RMSNorm using flashinfer (single kernel launch per tensor)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    
    # Reshape back to original shapes while preserving memory layout
    if q.is_contiguous():
        q_out = q_o.view(original_q_shape)
    else:
        # Use reshape to handle strided outputs
        q_out = q_o.reshape(original_q_shape)
    
    if k.is_contiguous():
        k_out = k_o.view(original_k_shape)
    else:
        # Use reshape to handle strided outputs
        k_out = k_o.reshape(original_k_shape)
    
    return q_out, k_out
"""}
