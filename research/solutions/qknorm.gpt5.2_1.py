import os
import torch
import flashinfer


def _rmsnorm_fallback(x: torch.Tensor, w: torch.Tensor, eps: float = 1e-6, out: torch.Tensor | None = None):
    x_f = x.float()
    w_f = w.float()
    inv_rms = torch.rsqrt(x_f.pow(2).mean(dim=-1, keepdim=True) + eps)
    y = (x_f * inv_rms) * w_f
    if out is None:
        return y.to(dtype=x.dtype)
    out.copy_(y.to(dtype=out.dtype))
    return out


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    if q_o.is_cuda and norm_weight.is_cuda:
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    else:
        _rmsnorm_fallback(q_2d, norm_weight, out=q_o)
        _rmsnorm_fallback(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    if q_o.is_cuda and norm_weight.is_cuda:
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    else:
        _rmsnorm_fallback(q, norm_weight, out=q_o)
        _rmsnorm_fallback(k, norm_weight, out=k_o)
    return q_o, k_o


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.shape[-1] != norm_weight.numel() or k.shape[-1] != norm_weight.numel():
        raise ValueError(
            f"hidden_dim mismatch: q[-1]={q.shape[-1]}, k[-1]={k.shape[-1]}, w={norm_weight.numel()}"
        )

    if not (q.is_cuda and k.is_cuda and norm_weight.is_cuda):
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        _rmsnorm_fallback(q, norm_weight, out=q_o)
        _rmsnorm_fallback(k, norm_weight, out=k_o)
        return q_o, k_o

    # Fast path: fuse q and k into one rmsnorm launch if they share storage/layout and same shape
    # Common for fused QKV output slicing when num_heads match.
    if (
        q.shape == k.shape
        and q.dtype == k.dtype
        and q.device == k.device
        and q.stride() == k.stride()
        and q.stride(-1) == 1
        and q.untyped_storage().data_ptr() == k.untyped_storage().data_ptr()
    ):
        q_off = q.storage_offset()
        k_off = k.storage_offset()
        delta = k_off - q_off
        if delta != 0:
            if delta > 0:
                base = q
                idx_q = 0
                idx_k = 1
                stride0 = delta
                storage_offset = q_off
                inner_stride = q.stride()
            else:
                base = k
                idx_k = 0
                idx_q = 1
                stride0 = -delta
                storage_offset = k_off
                inner_stride = k.stride()

            qk = torch.as_strided(
                base,
                size=(2,) + q.shape,
                stride=(stride0,) + inner_stride,
                storage_offset=storage_offset,
            )
            qk_o = torch.empty((2,) + q.shape, device=q.device, dtype=q.dtype)
            flashinfer.norm.rmsnorm(qk, norm_weight, out=qk_o)
            return qk_o[idx_q], qk_o[idx_k]

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


_KERNEL_CODE = r'''
import torch
import flashinfer

def _rmsnorm_fallback(x: torch.Tensor, w: torch.Tensor, eps: float = 1e-6, out: torch.Tensor | None = None):
    x_f = x.float()
    w_f = w.float()
    inv_rms = torch.rsqrt(x_f.pow(2).mean(dim=-1, keepdim=True) + eps)
    y = (x_f * inv_rms) * w_f
    if out is None:
        return y.to(dtype=x.dtype)
    out.copy_(y.to(dtype=out.dtype))
    return out

def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    if q_o.is_cuda and norm_weight.is_cuda:
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    else:
        _rmsnorm_fallback(q_2d, norm_weight, out=q_o)
        _rmsnorm_fallback(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)

def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    if q_o.is_cuda and norm_weight.is_cuda:
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    else:
        _rmsnorm_fallback(q, norm_weight, out=q_o)
        _rmsnorm_fallback(k, norm_weight, out=k_o)
    return q_o, k_o

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.shape[-1] != norm_weight.numel() or k.shape[-1] != norm_weight.numel():
        raise ValueError(
            f"hidden_dim mismatch: q[-1]={q.shape[-1]}, k[-1]={k.shape[-1]}, w={norm_weight.numel()}"
        )

    if not (q.is_cuda and k.is_cuda and norm_weight.is_cuda):
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        _rmsnorm_fallback(q, norm_weight, out=q_o)
        _rmsnorm_fallback(k, norm_weight, out=k_o)
        return q_o, k_o

    if (
        q.shape == k.shape
        and q.dtype == k.dtype
        and q.device == k.device
        and q.stride() == k.stride()
        and q.stride(-1) == 1
        and q.untyped_storage().data_ptr() == k.untyped_storage().data_ptr()
    ):
        q_off = q.storage_offset()
        k_off = k.storage_offset()
        delta = k_off - q_off
        if delta != 0:
            if delta > 0:
                base = q
                idx_q = 0
                idx_k = 1
                stride0 = delta
                storage_offset = q_off
                inner_stride = q.stride()
            else:
                base = k
                idx_k = 0
                idx_q = 1
                stride0 = -delta
                storage_offset = k_off
                inner_stride = k.stride()

            qk = torch.as_strided(
                base,
                size=(2,) + q.shape,
                stride=(stride0,) + inner_stride,
                storage_offset=storage_offset,
            )
            qk_o = torch.empty((2,) + q.shape, device=q.device, dtype=q.dtype)
            flashinfer.norm.rmsnorm(qk, norm_weight, out=qk_o)
            return qk_o[idx_q], qk_o[idx_k]

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}