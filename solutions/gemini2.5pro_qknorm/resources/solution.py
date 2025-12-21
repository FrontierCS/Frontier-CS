import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors by fusing them into a single operation.
    
    This implementation optimizes for launch overhead and memory access patterns by:
    1. Reshaping q and k to 2D tensors.
    2. Concatenating them into a single, larger, contiguous tensor.
    3. Applying flashinfer.norm.rmsnorm ONCE to this fused tensor.
    4. Splitting the result and reshaping it back to the original shapes.
    
    This reduces two kernel launches to one (plus a `torch.cat` kernel), which is
    beneficial for small, launch-bound operators. It avoids explicit `.contiguous()`
    calls on the inputs, instead relying on `torch.cat` to create an efficiently
    laid-out temporary tensor for the normalization step.
    
    Args:
        q: Query tensor of arbitrary shape (will be reshaped to 2D).
        k: Key tensor of arbitrary shape (will be reshaped to 2D).
        norm_weight: Normalization weight tensor of shape (hidden_dim,).
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors.
    """
    q_shape = q.shape
    k_shape = k.shape
    hidden_dim = q_shape[-1]
    
    q_2d = q.reshape(-1, hidden_dim)
    k_2d = k.reshape(-1, hidden_dim)
    
    q_rows = q_2d.shape[0]
    
    qk_fused = torch.cat((q_2d, k_2d), dim=0)
    
    qk_o_fused = torch.empty_like(qk_fused)
    
    flashinfer.norm.rmsnorm(qk_fused, norm_weight, out=qk_o_fused)
    
    q_o_2d = qk_o_fused[:q_rows]
    k_o_2d = qk_o_fused[q_rows:]
    
    q_o = q_o_2d.reshape(q_shape)
    k_o = k_o_2d.reshape(k_shape)
    
    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict containing the source code of the optimized qknorm function.
        """
        solution_code = """
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    \"\"\"
    Apply RMSNorm to query and key tensors by fusing them into a single operation.
    
    This implementation optimizes for launch overhead and memory access patterns by:
    1. Reshaping q and k to 2D tensors.
    2. Concatenating them into a single, larger, contiguous tensor.
    3. Applying flashinfer.norm.rmsnorm ONCE to this fused tensor.
    4. Splitting the result and reshaping it back to the original shapes.
    
    This reduces two kernel launches to one (plus a `torch.cat` kernel), which is
    beneficial for small, launch-bound operators. It avoids explicit `.contiguous()`
    calls on the inputs, instead relying on `torch.cat` to create an efficiently
    laid-out temporary tensor for the normalization step.
    
    Args:
        q: Query tensor of arbitrary shape (will be reshaped to 2D).
        k: Key tensor of arbitrary shape (will be reshaped to 2D).
        norm_weight: Normalization weight tensor of shape (hidden_dim,).
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors.
    \"\"\"
    q_shape = q.shape
    k_shape = k.shape
    hidden_dim = q_shape[-1]
    
    q_2d = q.reshape(-1, hidden_dim)
    k_2d = k.reshape(-1, hidden_dim)
    
    q_rows = q_2d.shape[0]
    
    qk_fused = torch.cat((q_2d, k_2d), dim=0)
    
    qk_o_fused = torch.empty_like(qk_fused)
    
    flashinfer.norm.rmsnorm(qk_fused, norm_weight, out=qk_o_fused)
    
    q_o_2d = qk_o_fused[:q_rows]
    k_o_2d = qk_o_fused[q_rows:]
    
    q_o = q_o_2d.reshape(q_shape)
    k_o = k_o_2d.reshape(k_shape)
    
    return q_o, k_o
"""
        return {"code": solution_code}
