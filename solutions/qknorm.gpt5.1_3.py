import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
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


def _optimized_rmsnorm(x: torch.Tensor, norm_weight: torch.Tensor) -> torch.Tensor:
    # Fast path for fully contiguous tensors: use a 2D view without extra copies.
    if x.is_contiguous():
        x_2d = x.view(-1, x.shape[-1])
        out_2d = torch.empty_like(x_2d)
        flashinfer.norm.rmsnorm(x_2d, norm_weight, out=out_2d)
        return out_2d.view_as(x)
    # For non-contiguous tensors (e.g., from fused QKV), avoid .contiguous()/transposes
    # to prevent extra memory traffic; rely on flashinfer to handle the strides.
    out = torch.empty_like(x)
    flashinfer.norm.rmsnorm(x, norm_weight, out=out)
    return out


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors.

    Args:
        q: Query tensor of arbitrary shape.
        k: Key tensor of arbitrary shape.
        norm_weight: Normalization weight tensor of shape (hidden_dim,).

    Returns:
        Tuple of (q_normalized, k_normalized) tensors.
    """
    hidden_dim = norm_weight.shape[0]
    if q.shape[-1] != hidden_dim:
        raise ValueError(
            f"Last dimension of q ({q.shape[-1]}) must match norm_weight ({hidden_dim})."
        )
    if k.shape[-1] != hidden_dim:
        raise ValueError(
            f"Last dimension of k ({k.shape[-1]}) must match norm_weight ({hidden_dim})."
        )

    q_o = _optimized_rmsnorm(q, norm_weight)
    k_o = _optimized_rmsnorm(k, norm_weight)
    return q_o, k_o
'''
        )
        return {"code": code}
