import torch
import flashinfer

# Ensure CUDA is available and properly initialize device
if not torch.cuda.is_available():
    raise RuntimeError("CUDA is not available. This benchmark requires a CUDA-enabled GPU.")
DEVICE = torch.device("cuda:0")
torch.cuda.set_device(DEVICE)


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Baseline qknorm implementation that directly applies RMSNorm to q and k tensors.
    This implementation is upstreamed by flashinfer community.
    Args:
        q: Query tensor of arbitrary shape
        k: Key tensor of arbitrary shape
        norm_weight: Normalization weight tensor

    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
