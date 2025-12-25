import os
import textwrap
from typing import Dict, Tuple, Optional

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


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    rmsnorm = flashinfer.norm.rmsnorm

    if q.numel() == 0 and k.numel() == 0:
        return torch.empty_like(q), torch.empty_like(k)

    same_dev = (q.device == k.device)
    same_dtype = (q.dtype == k.dtype)
    use_single_alloc = same_dev and same_dtype

    if use_single_alloc:
        total = q.numel() + k.numel()
        buf = torch.empty((total,), device=q.device, dtype=q.dtype)
        q_o = buf[: q.numel()].view(q.shape)
        k_o = buf[q.numel() :].view(k.shape)
    else:
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)

    rmsnorm(q, norm_weight, out=q_o)
    rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = textwrap.dedent(
            """
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

            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                rmsnorm = flashinfer.norm.rmsnorm

                if q.numel() == 0 and k.numel() == 0:
                    return torch.empty_like(q), torch.empty_like(k)

                same_dev = (q.device == k.device)
                same_dtype = (q.dtype == k.dtype)
                use_single_alloc = same_dev and same_dtype

                if use_single_alloc:
                    total = q.numel() + k.numel()
                    buf = torch.empty((total,), device=q.device, dtype=q.dtype)
                    q_o = buf[: q.numel()].view(q.shape)
                    k_o = buf[q.numel() :].view(k.shape)
                else:
                    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
                    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)

                rmsnorm(q, norm_weight, out=q_o)
                rmsnorm(k, norm_weight, out=k_o)
                return q_o, k_o
            """
        ).lstrip()
        return {"code": code}