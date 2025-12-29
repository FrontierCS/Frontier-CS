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


def _opt_rmsnorm(x: torch.Tensor, norm_weight: torch.Tensor):
    if x.is_cuda:
        if x.is_contiguous():
            x_2d = x.view(-1, x.shape[-1])
            out_2d = torch.empty_like(x_2d)
            flashinfer.norm.rmsnorm(x_2d, norm_weight, out=out_2d)
            return out_2d.view_as(x)
        else:
            out = torch.empty_like(x)
            flashinfer.norm.rmsnorm(x, norm_weight, out=out)
            return out
    else:
        eps = 1e-6
        w = norm_weight.to(device=x.device, dtype=x.dtype)
        var = x.pow(2).mean(dim=-1, keepdim=True)
        inv_rms = torch.rsqrt(var + eps)
        return x * inv_rms * w


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = _opt_rmsnorm(q, norm_weight)
    k_o = _opt_rmsnorm(k, norm_weight)
    return q_o, k_o


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
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


def _opt_rmsnorm(x: torch.Tensor, norm_weight: torch.Tensor):
    if x.is_cuda:
        if x.is_contiguous():
            x_2d = x.view(-1, x.shape[-1])
            out_2d = torch.empty_like(x_2d)
            flashinfer.norm.rmsnorm(x_2d, norm_weight, out=out_2d)
            return out_2d.view_as(x)
        else:
            out = torch.empty_like(x)
            flashinfer.norm.rmsnorm(x, norm_weight, out=out)
            return out
    else:
        eps = 1e-6
        w = norm_weight.to(device=x.device, dtype=x.dtype)
        var = x.pow(2).mean(dim=-1, keepdim=True)
        inv_rms = torch.rsqrt(var + eps)
        return x * inv_rms * w


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = _opt_rmsnorm(q, norm_weight)
    k_o = _opt_rmsnorm(k, norm_weight)
    return q_o, k_o
'''
        return {"code": code}