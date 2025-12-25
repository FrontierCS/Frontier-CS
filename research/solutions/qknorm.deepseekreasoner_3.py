import torch
import flashinfer
from typing import Tuple

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    # Reshape to 2D without forcing contiguous if already correct layout
    q_shape = q.shape
    k_shape = k.shape
    
    # Check if last dimension is contiguous
    q_last_dim = q_shape[-1]
    k_last_dim = k_shape[-1]
    
    # Efficient reshaping without unnecessary copies
    if q.is_contiguous() and q.dim() > 2:
        q_2d = q.view(-1, q_last_dim)
    else:
        # If non-contiguous, check if we can view without copy
        if q.stride(-1) == 1 and q.numel() == q.size(-1) * (q.numel() // q.size(-1)):
            q_2d = q.view(-1, q_last_dim)
        else:
            q_2d = q.reshape(-1, q_last_dim)
    
    if k.is_contiguous() and k.dim() > 2:
        k_2d = k.view(-1, k_last_dim)
    else:
        if k.stride(-1) == 1 and k.numel() == k.size(-1) * (k.numel() // k.size(-1)):
            k_2d = k.view(-1, k_last_dim)
        else:
            k_2d = k.reshape(-1, k_last_dim)
    
    # Use single kernel launch when possible by processing both tensors
    # Create output tensors with optimal memory layout
    q_o_2d = torch.empty_like(q_2d)
    k_o_2d = torch.empty_like(k_2d)
    
    # Apply RMSNorm - flashinfer handles efficient kernel launches
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o_2d)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o_2d)
    
    # Reshape back to original shape
    return q_o_2d.view(q_shape), k_o_2d.view(k_shape)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """import torch
import flashinfer
from typing import Tuple

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    # Reshape to 2D without forcing contiguous if already correct layout
    q_shape = q.shape
    k_shape = k.shape
    
    # Check if last dimension is contiguous
    q_last_dim = q_shape[-1]
    k_last_dim = k_shape[-1]
    
    # Efficient reshaping without unnecessary copies
    if q.is_contiguous() and q.dim() > 2:
        q_2d = q.view(-1, q_last_dim)
    else:
        # If non-contiguous, check if we can view without copy
        if q.stride(-1) == 1 and q.numel() == q.size(-1) * (q.numel() // q.size(-1)):
            q_2d = q.view(-1, q_last_dim)
        else:
            q_2d = q.reshape(-1, q_last_dim)
    
    if k.is_contiguous() and k.dim() > 2:
        k_2d = k.view(-1, k_last_dim)
    else:
        if k.stride(-1) == 1 and k.numel() == k.size(-1) * (k.numel() // k.size(-1)):
            k_2d = k.view(-1, k_last_dim)
        else:
            k_2d = k.reshape(-1, k_last_dim)
    
    # Use single kernel launch when possible by processing both tensors
    # Create output tensors with optimal memory layout
    q_o_2d = torch.empty_like(q_2d)
    k_o_2d = torch.empty_like(k_2d)
    
    # Apply RMSNorm - flashinfer handles efficient kernel launches
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o_2d)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o_2d)
    
    # Reshape back to original shape
    return q_o_2d.view(q_shape), k_o_2d.view(k_shape)
"""}
