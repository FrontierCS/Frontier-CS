import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import flashinfer

            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                q_o = torch.empty_like(q)
                k_o = torch.empty_like(k)
                flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
                flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
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
        """)
        return {"code": code}