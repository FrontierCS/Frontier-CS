import os
import textwrap
from typing import Dict, Optional

import torch
import flashinfer


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.device.type != "cuda" or k.device.type != "cuda":
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        xq = q.contiguous() if q.stride(-1) != 1 else q
        xk = k.contiguous() if k.stride(-1) != 1 else k
        w = norm_weight.contiguous() if not norm_weight.is_contiguous() else norm_weight
        flashinfer.norm.rmsnorm(xq, w, out=q_o)
        flashinfer.norm.rmsnorm(xk, w, out=k_o)
        return q_o, k_o

    if norm_weight.device != q.device:
        raise RuntimeError("norm_weight must be on the same device as q/k")
    if q.shape[-1] != norm_weight.shape[0] or k.shape[-1] != norm_weight.shape[0]:
        raise RuntimeError("Last dim of q/k must match norm_weight shape[0]")

    w = norm_weight if norm_weight.is_contiguous() else norm_weight.contiguous()

    xq = q if q.stride(-1) == 1 else q.contiguous()
    xk = k if k.stride(-1) == 1 else k.contiguous()

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)

    flashinfer.norm.rmsnorm(xq, w, out=q_o)
    flashinfer.norm.rmsnorm(xk, w, out=k_o)
    return q_o, k_o


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = r"""
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.device.type != "cuda" or k.device.type != "cuda":
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        xq = q.contiguous() if q.stride(-1) != 1 else q
        xk = k.contiguous() if k.stride(-1) != 1 else k
        w = norm_weight.contiguous() if not norm_weight.is_contiguous() else norm_weight
        flashinfer.norm.rmsnorm(xq, w, out=q_o)
        flashinfer.norm.rmsnorm(xk, w, out=k_o)
        return q_o, k_o

    if norm_weight.device != q.device:
        raise RuntimeError("norm_weight must be on the same device as q/k")
    if q.shape[-1] != norm_weight.shape[0] or k.shape[-1] != norm_weight.shape[0]:
        raise RuntimeError("Last dim of q/k must match norm_weight shape[0]")

    w = norm_weight if norm_weight.is_contiguous() else norm_weight.contiguous()

    xq = q if q.stride(-1) == 1 else q.contiguous()
    xk = k if k.stride(-1) == 1 else k.contiguous()

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)

    flashinfer.norm.rmsnorm(xq, w, out=q_o)
    flashinfer.norm.rmsnorm(xk, w, out=k_o)
    return q_o, k_o

def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)
"""
        return {"code": textwrap.dedent(code).lstrip()}