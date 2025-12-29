import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    orig_q_shape = q.shape
    q_dim = orig_q_shape[-1]
    q_flat = q.view(-1, q_dim)
    q_out_flat = torch.empty(q_flat.shape, dtype=q.dtype, device=q.device)
    flashinfer.norm.rmsnorm(q_flat, norm_weight, out=q_out_flat)
    q_out = q_out_flat.view(orig_q_shape)
    
    orig_k_shape = k.shape
    k_dim = orig_k_shape[-1]
    k_flat = k.view(-1, k_dim)
    k_out_flat = torch.empty(k_flat.shape, dtype=k.dtype, device=k.device)
    flashinfer.norm.rmsnorm(k_flat, norm_weight, out=k_out_flat)
    k_out = k_out_flat.view(orig_k_shape)
    
    return q_out, k_out
"""
        return {"code": code}