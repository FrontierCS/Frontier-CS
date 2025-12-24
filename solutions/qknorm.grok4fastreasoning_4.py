import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
"""
        return {"code": code}
