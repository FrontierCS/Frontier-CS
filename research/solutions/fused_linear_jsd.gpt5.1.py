import torch
import triton
import triton.language as tl
import inspect
import textwrap


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
    # Compute linear layers using fast half-precision matmul, then upcast to float32
    logits1 = torch.matmul(X, W1).to(torch.float32)
    logits2 = torch.matmul(X, W2).to(torch.float32)

    # Add biases (float32 for numerical stability)
    logits1 = logits1 + B1
    logits2 = logits2 + B2

    # Stable log-softmax for both sets of logits
    log_p = torch.nn.functional.log_softmax(logits1, dim=-1)
    log_q = torch.nn.functional.log_softmax(logits2, dim=-1)

    # Probabilities
    p = log_p.exp()
    q = log_q.exp()

    # Mixture distribution
    m = 0.5 * (p + q)
    eps = 1e-20
    m_clamped = m.clamp_min(eps)
    log_m = m_clamped.log()

    # Entropies
    H_p = -(p * log_p).sum(dim=-1)
    H_q = -(q * log_q).sum(dim=-1)
    H_m = -(m * log_m).sum(dim=-1)

    # Jensen-Shannon Divergence: JSD = H(M) - 0.5 * H(P) - 0.5 * H(Q)
    jsd = H_m - 0.5 * H_p - 0.5 * H_q
    return jsd.to(torch.float32)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        fused_src = textwrap.dedent(inspect.getsource(fused_linear_jsd))
        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            f"{fused_src}\n"
        )
        return {"code": code}
