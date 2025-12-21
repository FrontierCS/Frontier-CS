import torch
import flashinfer
from typing import Optional, Dict


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors without unnecessary re-layout.

    Args:
        q: Query tensor of arbitrary shape.
        k: Key tensor of arbitrary shape.
        norm_weight: Normalization weight of shape (hidden_dim,).

    Returns:
        Tuple of (q_normalized, k_normalized).
    """
    hidden_dim_q = q.shape[-1]
    hidden_dim_k = k.shape[-1]

    q_numel = q.numel()
    k_numel = k.numel()

    same_device_and_dtype = (q.device == k.device) and (q.dtype == k.dtype)

    if same_device_and_dtype and (q_numel + k_numel > 0):
        # Single allocation for both q and k outputs to reduce allocator overhead
        out_flat = torch.empty(q_numel + k_numel, device=q.device, dtype=q.dtype)
        q_out_flat = out_flat[:q_numel]
        k_out_flat = out_flat[q_numel:]
    else:
        q_out_flat = torch.empty(q_numel, device=q.device, dtype=q.dtype)
        k_out_flat = torch.empty(k_numel, device=k.device, dtype=k.dtype)

    # Normalize q
    if q_numel > 0:
        if q.is_contiguous():
            # Fast path: flatten to 2D without copies
            q_in_2d = q.view(-1, hidden_dim_q)
            q_out_2d = q_out_flat.view_as(q_in_2d)
            flashinfer.norm.rmsnorm(q_in_2d, norm_weight, out=q_out_2d)
            q_o = q_out_2d.view(q.shape)
        else:
            # General path: operate on potentially non-contiguous tensor directly
            q_out = q_out_flat.view(q.shape)
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_out)
            q_o = q_out
    else:
        q_o = q_out_flat.view(q.shape)

    # Normalize k
    if k_numel > 0:
        if k.is_contiguous():
            # Fast path: flatten to 2D without copies
            k_in_2d = k.view(-1, hidden_dim_k)
            k_out_2d = k_out_flat.view_as(k_in_2d)
            flashinfer.norm.rmsnorm(k_in_2d, norm_weight, out=k_out_2d)
            k_o = k_out_2d.view(k.shape)
        else:
            # General path: operate on potentially non-contiguous tensor directly
            k_out = k_out_flat.view(k.shape)
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_out)
            k_o = k_out
    else:
        k_o = k_out_flat.view(k.shape)

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
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        import inspect

        qknorm_src = inspect.getsource(qknorm)
        default_src = inspect.getsource(default_qknorm)
        customized_src = inspect.getsource(customized_qknorm)

        code = (
            "import torch\n"
            "import flashinfer\n\n"
            f"{qknorm_src}\n\n"
            f"{default_src}\n\n"
            f"{customized_src}\n"
        )

        return {"code": code}
