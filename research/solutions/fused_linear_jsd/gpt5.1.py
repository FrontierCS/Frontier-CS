import textwrap

CODE = r'''
import torch
import triton
import triton.language as tl
import torch.nn.functional as F


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    Args:
        X: (M, K) float16
        W1: (K, N) float16
        B1: (N,) float32
        W2: (K, N) float16
        B2: (N,) float32
    Returns:
        (M,) float32 JSD per sample
    """
    # Linear layers in float16, accumulate / subsequent ops in float32
    logits1 = torch.matmul(X, W1).to(torch.float32) + B1
    logits2 = torch.matmul(X, W2).to(torch.float32) + B2

    # Softmax probabilities (numerically stable implementation from PyTorch)
    P = F.softmax(logits1, dim=-1)
    Q = F.softmax(logits2, dim=-1)

    # Jensen-Shannon Divergence
    M = 0.5 * (P + Q)
    eps = 1e-8

    logP = torch.log(P + eps)
    logQ = torch.log(Q + eps)
    logM = torch.log(M + eps)

    kl_pm = (P * (logP - logM)).sum(dim=-1)
    kl_qm = (Q * (logQ - logM)).sum(dim=-1)
    jsd = 0.5 * (kl_pm + kl_qm)
    return jsd
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": CODE}