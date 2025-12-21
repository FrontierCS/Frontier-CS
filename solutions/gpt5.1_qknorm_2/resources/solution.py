import textwrap
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


def _rmsnorm_optimized(x: torch.Tensor, norm_weight: torch.Tensor) -> torch.Tensor:
    hidden_dim = x.shape[-1]
    if x.is_contiguous():
        x_2d = x.view(-1, hidden_dim)
        out_2d = torch.empty_like(x_2d)
        flashinfer.norm.rmsnorm(x_2d, norm_weight, out=out_2d)
        return out_2d.view_as(x)
    else:
        out = torch.empty_like(x)
        flashinfer.norm.rmsnorm(x, norm_weight, out=out)
        return out


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors.

    Args:
        q: Query tensor of arbitrary shape
        k: Key tensor of arbitrary shape
        norm_weight: Normalization weight tensor of shape (hidden_dim,)

    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    q_o = _rmsnorm_optimized(q, norm_weight)
    k_o = _rmsnorm_optimized(k, norm_weight)
    return q_o, k_o


class Solution:
    def solve(self, spec_path: str = None) -> dict:
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


            def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
                k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
                flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
                flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
                return q_o, k_o


            def _rmsnorm_optimized(x: torch.Tensor, norm_weight: torch.Tensor) -> torch.Tensor:
                hidden_dim = x.shape[-1]
                if x.is_contiguous():
                    x_2d = x.view(-1, hidden_dim)
                    out_2d = torch.empty_like(x_2d)
                    flashinfer.norm.rmsnorm(x_2d, norm_weight, out=out_2d)
                    return out_2d.view_as(x)
                else:
                    out = torch.empty_like(x)
                    flashinfer.norm.rmsnorm(x, norm_weight, out=out)
                    return out


            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                \"""
                Apply RMSNorm to query and key tensors.

                Args:
                    q: Query tensor of arbitrary shape
                    k: Key tensor of arbitrary shape
                    norm_weight: Normalization weight tensor of shape (hidden_dim,)

                Returns:
                    Tuple of (q_normalized, k_normalized) tensors
                \"""
                q_o = _rmsnorm_optimized(q, norm_weight)
                k_o = _rmsnorm_optimized(k, norm_weight)
                return q_o, k_o
            """
        )
        return {"code": code}
