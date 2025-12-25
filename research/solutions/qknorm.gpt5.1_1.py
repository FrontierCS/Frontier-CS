import torch
import flashinfer
from typing import Dict, Any, Optional


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


def _rmsnorm_cpu(x: torch.Tensor, norm_weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    orig_dtype = x.dtype
    x_f = x.to(torch.float32)
    w_f = norm_weight.to(torch.float32)
    mean_square = x_f.pow(2).mean(dim=-1, keepdim=True)
    x_norm = x_f * torch.rsqrt(mean_square + eps)
    y = x_norm * w_f
    return y.to(orig_dtype)


def _rmsnorm_gpu(x: torch.Tensor, norm_weight: torch.Tensor) -> torch.Tensor:
    if x.is_contiguous():
        orig_shape = x.shape
        x_2d = x.view(-1, orig_shape[-1])
        y_2d = torch.empty_like(x_2d)
        flashinfer.norm.rmsnorm(x_2d, norm_weight, out=y_2d)
        return y_2d.view(orig_shape)
    else:
        y = torch.empty_like(x)
        flashinfer.norm.rmsnorm(x, norm_weight, out=y)
        return y


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors.
    """
    if q.device != k.device:
        raise ValueError("q and k must be on the same device")

    if norm_weight.device != q.device:
        norm_weight = norm_weight.to(q.device)

    if not q.is_cuda:
        q_o = _rmsnorm_cpu(q, norm_weight)
        k_o = _rmsnorm_cpu(k, norm_weight)
    else:
        q_o = _rmsnorm_gpu(q, norm_weight)
        k_o = _rmsnorm_gpu(k, norm_weight)

    return q_o, k_o


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, Any]:
        # Use this file itself as the program containing qknorm
        return {"program_path": __file__}
