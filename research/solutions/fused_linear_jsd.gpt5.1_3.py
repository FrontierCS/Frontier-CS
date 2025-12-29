import torch
import torch.nn.functional as F
import triton
import triton.language as tl


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    X32 = X.float()
    W1_32 = W1.float()
    W2_32 = W2.float()

    logits1 = X32.matmul(W1_32)
    logits1 = logits1 + B1

    logits2 = X32.matmul(W2_32)
    logits2 = logits2 + B2

    log_p = F.log_softmax(logits1, dim=-1)
    log_q = F.log_softmax(logits2, dim=-1)

    p = log_p.exp()
    q = log_q.exp()

    m = 0.5 * (p + q)
    eps = 1e-20
    log_m = torch.log(m.clamp_min(eps))

    kl_p_m = torch.sum(p * (log_p - log_m), dim=-1)
    kl_q_m = torch.sum(q * (log_q - log_m), dim=-1)

    jsd = 0.5 * (kl_p_m + kl_q_m)
    return jsd


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}