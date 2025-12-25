import os
import torch
import flashinfer

def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)

def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o

def _apply_rmsnorm_maybe_flatten(x: torch.Tensor, norm_weight: torch.Tensor) -> torch.Tensor:
    hidden = x.shape[-1]
    # Prefer flatten to 2D only when it's a true view (i.e., contiguous) to avoid copies
    if x.is_contiguous():
        x2d = x.view(-1, hidden)
        out = torch.empty_like(x)
        out2d = out.view(-1, hidden)
        flashinfer.norm.rmsnorm(x2d, norm_weight, out=out2d)
        return out
    else:
        # Keep original striding; allocate output preserving format to avoid extra copies
        out = torch.empty_like(x)
        flashinfer.norm.rmsnorm(x, norm_weight, out=out)
        return out

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = _apply_rmsnorm_maybe_flatten(q, norm_weight)
    k_o = _apply_rmsnorm_maybe_flatten(k, norm_weight)
    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
