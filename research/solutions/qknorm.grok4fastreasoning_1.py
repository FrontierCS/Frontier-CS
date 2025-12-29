class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    hidden_dim = q.shape[-1]
    assert k.shape[-1] == hidden_dim, "Q and K must have same hidden dimension"
    q_2d = q.view(-1, hidden_dim)
    k_2d = k.view(-1, hidden_dim)
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)
"""
        return {"code": code}