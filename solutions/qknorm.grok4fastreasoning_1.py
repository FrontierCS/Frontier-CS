import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    d = q.shape[-1]
    q_2d = q.view(-1, d)
    k_2d = k.view(-1, d)
    q_out_2d = torch.empty(q_2d.shape, dtype=q.dtype, device=q.device)
    k_out_2d = torch.empty(k_2d.shape, dtype=k.dtype, device=k.device)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_out_2d)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_out_2d)
    return q_out_2d.view(q.shape), k_out_2d.view(k.shape)
"""
        return {"code": code}
