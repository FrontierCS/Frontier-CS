import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import flashinfer

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using FlashInfer with stream parallelism.
    
    Args:
        q: Query tensor of arbitrary shape
        k: Key tensor of arbitrary shape
        norm_weight: Normalization weight tensor
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    # Allocate contiguous memory for outputs
    # Using empty() is faster than empty_like() and ensures contiguous layout
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    # Create a secondary stream to parallelize the normalization of k
    # This helps hide kernel launch overhead and memory latency
    stream_k = torch.cuda.Stream()
    
    # Launch k normalization on the secondary stream
    with torch.cuda.stream(stream_k):
        # flashinfer.norm.rmsnorm is highly optimized.
        # It handles the normalization over the last dimension.
        # If inputs are non-contiguous, the underlying kernel/dispatcher handles data access.
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    
    # Launch q normalization on the current stream
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    
    # Ensure k processing is complete before returning
    # This makes the operation safe for the caller on the current stream
    torch.cuda.current_stream().wait_stream(stream_k)
    
    return q_o, k_o
"""
        return {"code": code}