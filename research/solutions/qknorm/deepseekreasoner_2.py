import torch
import flashinfer
import torch.nn.functional as F
from typing import Tuple

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Apply RMSNorm to query and key tensors with optimized memory access.
    """
    # Save original shapes for output
    orig_q_shape = q.shape
    orig_k_shape = k.shape
    
    # Get last dimension (hidden_dim)
    hidden_dim = q.shape[-1]
    
    # Reshape to 2D without copying if already contiguous in last dimension
    if q.is_contiguous() or q.stride(-1) == 1:
        q_2d = q.view(-1, hidden_dim)
    else:
        # For non-contiguous tensors, use reshape which handles striding
        q_2d = q.reshape(-1, hidden_dim)
    
    if k.is_contiguous() or k.stride(-1) == 1:
        k_2d = k.view(-1, hidden_dim)
    else:
        k_2d = k.reshape(-1, hidden_dim)
    
    # Pre-allocate output tensors with optimal memory layout
    if q_2d.is_contiguous():
        q_o = torch.empty_like(q_2d)
    else:
        q_o = torch.empty(q_2d.shape, device=q.device, dtype=q.dtype, memory_format=torch.contiguous_format)
    
    if k_2d.is_contiguous():
        k_o = torch.empty_like(k_2d)
    else:
        k_o = torch.empty(k_2d.shape, device=k.device, dtype=k.dtype, memory_format=torch.contiguous_format)
    
    # Apply RMSNorm using flashinfer
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    
    # Reshape back to original shapes
    return q_o.view(orig_q_shape), k_o.view(orig_k_shape)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import flashinfer
import torch.nn.functional as F
from typing import Tuple

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    \"\"\"
    Apply RMSNorm to query and key tensors with optimized memory access.
    \"\"\"
    # Save original shapes for output
    orig_q_shape = q.shape
    orig_k_shape = k.shape
    
    # Get last dimension (hidden_dim)
    hidden_dim = q.shape[-1]
    
    # Reshape to 2D without copying if already contiguous in last dimension
    if q.is_contiguous() or q.stride(-1) == 1:
        q_2d = q.view(-1, hidden_dim)
    else:
        # For non-contiguous tensors, use reshape which handles striding
        q_2d = q.reshape(-1, hidden_dim)
    
    if k.is_contiguous() or k.stride(-1) == 1:
        k_2d = k.view(-1, hidden_dim)
    else:
        k_2d = k.reshape(-1, hidden_dim)
    
    # Pre-allocate output tensors with optimal memory layout
    if q_2d.is_contiguous():
        q_o = torch.empty_like(q_2d)
    else:
        q_o = torch.empty(q_2d.shape, device=q.device, dtype=q.dtype, memory_format=torch.contiguous_format)
    
    if k_2d.is_contiguous():
        k_o = torch.empty_like(k_2d)
    else:
        k_o = torch.empty(k_2d.shape, device=k.device, dtype=k.dtype, memory_format=torch.contiguous_format)
    
    # Apply RMSNorm using flashinfer
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    
    # Reshape back to original shapes
    return q_o.view(orig_q_shape), k_o.view(orig_k_shape)
"""}