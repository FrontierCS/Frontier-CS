import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    dim = q.shape[-1]
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    q_2d = q.view(-1, dim)
    q_out_2d = q_o.view(-1, dim)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_out_2d)
    k_2d = k.view(-1, dim)
    k_out_2d = k_o.view(-1, dim)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_out_2d)
    return q_o, k_o
"""
        return {"code": code}
