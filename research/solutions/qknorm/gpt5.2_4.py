import os
import textwrap
from typing import Dict, Tuple, Optional

import torch

try:
    import flashinfer  # type: ignore
except Exception:
    flashinfer = None


def _cpu_rmsnorm(x: torch.Tensor, w: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    x_f = x.float()
    w_f = w.float()
    inv_rms = torch.rsqrt(x_f.pow(2).mean(dim=-1, keepdim=True) + eps)
    y = x_f * inv_rms * w_f
    return y.to(dtype=x.dtype)


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if flashinfer is None or (q.device.type != "cuda"):
        return _cpu_rmsnorm(q, norm_weight), _cpu_rmsnorm(k, norm_weight)

    rmsnorm = flashinfer.norm.rmsnorm

    if (
        q.device == k.device
        and q.dtype == k.dtype
        and q.shape == k.shape
        and q.stride() == k.stride()
    ):
        try:
            if q.untyped_storage().data_ptr() == k.untyped_storage().data_ptr():
                q_off = q.storage_offset()
                k_off = k.storage_offset()
                if q_off != k_off:
                    if q_off < k_off:
                        base = q
                        diff = k_off - q_off
                        swap = False
                    else:
                        base = k
                        diff = q_off - k_off
                        swap = True
                    in_view = base.as_strided((2,) + q.shape, (diff,) + q.stride())
                    out = torch.empty((2,) + q.shape, device=q.device, dtype=q.dtype)
                    rmsnorm(in_view, norm_weight, out=out)
                    if swap:
                        return out[1], out[0]
                    return out[0], out[1]
        except Exception:
            pass

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    rmsnorm(q, norm_weight, out=q_o)
    rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if flashinfer is None or (q.device.type != "cuda"):
        q_2d = q.contiguous().view(-1, q.shape[-1])
        k_2d = k.contiguous().view(-1, k.shape[-1])
        q_o = _cpu_rmsnorm(q_2d, norm_weight).view(q.shape)
        k_o = _cpu_rmsnorm(k_2d, norm_weight).view(k.shape)
        return q_o, k_o

    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import flashinfer

    def _cpu_rmsnorm(x: torch.Tensor, w: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        x_f = x.float()
        w_f = w.float()
        inv_rms = torch.rsqrt(x_f.pow(2).mean(dim=-1, keepdim=True) + eps)
        y = x_f * inv_rms * w_f
        return y.to(dtype=x.dtype)

    _rmsnorm = flashinfer.norm.rmsnorm

    def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
        if q.device.type != "cuda":
            return _cpu_rmsnorm(q, norm_weight), _cpu_rmsnorm(k, norm_weight)

        if (
            q.device == k.device
            and q.dtype == k.dtype
            and q.shape == k.shape
            and q.stride() == k.stride()
        ):
            try:
                if q.untyped_storage().data_ptr() == k.untyped_storage().data_ptr():
                    q_off = q.storage_offset()
                    k_off = k.storage_offset()
                    if q_off != k_off:
                        if q_off < k_off:
                            base = q
                            diff = k_off - q_off
                            swap = False
                        else:
                            base = k
                            diff = q_off - k_off
                            swap = True
                        in_view = base.as_strided((2,) + q.shape, (diff,) + q.stride())
                        out = torch.empty((2,) + q.shape, device=q.device, dtype=q.dtype)
                        _rmsnorm(in_view, norm_weight, out=out)
                        if swap:
                            return out[1], out[0]
                        return out[0], out[1]
            except Exception:
                pass

        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        _rmsnorm(q, norm_weight, out=q_o)
        _rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
        q_2d = q.contiguous().view(-1, q.shape[-1])
        k_2d = k.contiguous().view(-1, k.shape[-1])
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        _rmsnorm(q_2d, norm_weight, out=q_o)
        _rmsnorm(k_2d, norm_weight, out=k_o)
        return q_o.view(q.shape), k_o.view(k.shape)
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        return {"code": _KERNEL_CODE}