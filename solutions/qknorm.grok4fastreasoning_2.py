import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    D = q.shape[-1]
    q_2d = q.view(-1, D)
    if q_2d.stride(0) != D:
        q_2d = q_2d.contiguous()
    q_o_2d = torch.empty_like(q_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o_2d)
    q_o = q_o_2d.view(q.shape)

    Dk = k.shape[-1]
    k_2d = k.view(-1, Dk)
    if k_2d.stride(0) != Dk:
        k_2d = k_2d.contiguous()
    k_o_2d = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o_2d)
    k_o = k_o_2d.view(k.shape)

    return q_o, k_o
"""
        return {"code": code}
