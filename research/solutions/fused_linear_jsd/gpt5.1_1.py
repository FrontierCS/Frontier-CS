import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent('''\
import torch
import triton
import triton.language as tl
import torch.nn.functional as F


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.

    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)

    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    # Ensure computations are done in float32 for numerical stability
    logits1 = torch.matmul(X, W1).to(torch.float32)
    logits2 = torch.matmul(X, W2).to(torch.float32)

    logits1 = logits1 + B1
    logits2 = logits2 + B2

    # Stable log-softmax for both sets of logits
    logP = F.log_softmax(logits1, dim=-1)
    logQ = F.log_softmax(logits2, dim=-1)

    P = torch.exp(logP)
    Q = torch.exp(logQ)

    # Mixture distribution M = 0.5 * (P + Q)
    M = 0.5 * (P + Q)

    eps = 1e-9
    logM = torch.log(M + eps)

    # KL divergences
    kl_PM = torch.sum(P * (logP - logM), dim=-1)
    kl_QM = torch.sum(Q * (logQ - logM), dim=-1)

    jsd = 0.5 * (kl_PM + kl_QM)
    return jsd.to(torch.float32)
''')
        return {"code": kernel_code}