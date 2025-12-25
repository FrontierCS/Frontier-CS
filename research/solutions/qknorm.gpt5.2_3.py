import os
import textwrap
import torch
import flashinfer


def _maybe_flatten_last_dim(x: torch.Tensor):
    if x.is_contiguous():
        hd = x.shape[-1]
        return x.view(-1, hd), True
    return x, False


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.shape[-1] != norm_weight.shape[0] or k.shape[-1] != norm_weight.shape[0]:
        raise ValueError(
            f"hidden_dim mismatch: q[-1]={q.shape[-1]}, k[-1]={k.shape[-1]}, w[0]={norm_weight.shape[0]}"
        )
    if q.device != k.device or q.dtype != k.dtype:
        raise ValueError("q and k must have the same device and dtype")
    if norm_weight.device != q.device:
        raise ValueError("norm_weight must be on the same device as q/k")

    if norm_weight.ndim != 1:
        norm_weight = norm_weight.view(-1)
    if not norm_weight.is_contiguous():
        norm_weight = norm_weight.contiguous()

    q_in, q_flattened = _maybe_flatten_last_dim(q)
    k_in, k_flattened = _maybe_flatten_last_dim(k)

    q_o = torch.empty(q_in.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k_in.shape, device=k.device, dtype=k.dtype)

    try:
        flashinfer.norm.rmsnorm(q_in, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_in, norm_weight, out=k_o)
    except Exception:
        # Fallback (primarily for non-CUDA or unsupported cases)
        eps = 1e-6
        q_var = q_in.to(torch.float32).pow(2).mean(dim=-1, keepdim=True)
        k_var = k_in.to(torch.float32).pow(2).mean(dim=-1, keepdim=True)
        q_norm = q_in * torch.rsqrt(q_var + eps).to(q_in.dtype)
        k_norm = k_in * torch.rsqrt(k_var + eps).to(k_in.dtype)
        q_o.copy_(q_norm * norm_weight)
        k_o.copy_(k_norm * norm_weight)

    if q_flattened:
        q_o = q_o.view(q.shape)
    if k_flattened:
        k_o = k_o.view(k.shape)
    return q_o, k_o


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


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import torch
            import flashinfer

            def _maybe_flatten_last_dim(x: torch.Tensor):
                if x.is_contiguous():
                    hd = x.shape[-1]
                    return x.view(-1, hd), True
                return x, False

            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                if q.shape[-1] != norm_weight.shape[0] or k.shape[-1] != norm_weight.shape[0]:
                    raise ValueError(
                        f"hidden_dim mismatch: q[-1]={q.shape[-1]}, k[-1]={k.shape[-1]}, w[0]={norm_weight.shape[0]}"
                    )
                if q.device != k.device or q.dtype != k.dtype:
                    raise ValueError("q and k must have the same device and dtype")
                if norm_weight.device != q.device:
                    raise ValueError("norm_weight must be on the same device as q/k")

                if norm_weight.ndim != 1:
                    norm_weight = norm_weight.view(-1)
                if not norm_weight.is_contiguous():
                    norm_weight = norm_weight.contiguous()

                q_in, q_flattened = _maybe_flatten_last_dim(q)
                k_in, k_flattened = _maybe_flatten_last_dim(k)

                q_o = torch.empty(q_in.shape, device=q.device, dtype=q.dtype)
                k_o = torch.empty(k_in.shape, device=k.device, dtype=k.dtype)

                flashinfer.norm.rmsnorm(q_in, norm_weight, out=q_o)
                flashinfer.norm.rmsnorm(k_in, norm_weight, out=k_o)

                if q_flattened:
                    q_o = q_o.view(q.shape)
                if k_flattened:
                    k_o = k_o.view(k.shape)
                return q_o, k_o
            """
        ).lstrip()
        return {"code": code}