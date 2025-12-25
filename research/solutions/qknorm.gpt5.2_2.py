import os
import textwrap


KERNEL_CODE = r"""
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


def _same_storage(a: torch.Tensor, b: torch.Tensor) -> bool:
    try:
        return a.untyped_storage().data_ptr() == b.untyped_storage().data_ptr()
    except Exception:
        return False


def _try_make_fused_qk_view(q: torch.Tensor, k: torch.Tensor):
    if q.device != k.device or q.dtype != k.dtype:
        return None
    if q.shape != k.shape:
        return None
    if q.stride() != k.stride():
        return None
    if not _same_storage(q, k):
        return None

    dq = int(q.storage_offset())
    dk = int(k.storage_offset())
    delta = dk - dq
    if delta <= 0:
        return None

    # Create a view x such that x[0] == q and x[1] == k (same strides, same base storage).
    try:
        x = q.as_strided(
            size=(2,) + tuple(q.shape),
            stride=(delta,) + tuple(q.stride()),
            storage_offset=dq,
        )
    except Exception:
        return None
    return x


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    x = _try_make_fused_qk_view(q, k)
    if x is not None:
        y = torch.empty((2,) + tuple(q.shape), device=q.device, dtype=q.dtype)
        flashinfer.norm.rmsnorm(x, norm_weight, out=y)
        return y[0], y[1]

    # Fallback: two calls. Use a single allocation when possible.
    if q.device == k.device and q.dtype == k.dtype:
        total = q.numel() + k.numel()
        buf = torch.empty((total,), device=q.device, dtype=q.dtype)
        q_o = buf[: q.numel()].view(q.shape)
        k_o = buf[q.numel() :].view(k.shape)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
"""


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": textwrap.dedent(KERNEL_CODE).lstrip()}