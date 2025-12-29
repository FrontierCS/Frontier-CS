import torch
import flashinfer
import os

# By using global streams, we avoid the overhead of creating new streams on every call.
# This is crucial for a performance-sensitive, frequently called function.
_QK_NORM_STREAMS = None

def _get_qknorm_streams():
    """Initializes and returns a tuple of two CUDA streams for parallel execution."""
    global _QK_NORM_STREAMS
    if _QK_NORM_STREAMS is None:
        # Create two separate streams for query and key normalization.
        _QK_NORM_STREAMS = (torch.cuda.Stream(), torch.cuda.Stream())
    return _QK_NORM_STREAMS

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors in parallel using CUDA streams.

    This implementation optimizes the qknorm operation by leveraging task-level
    parallelism. The normalization of the query (q) and key (k) tensors are
    independent operations. By executing them on separate CUDA streams, we can
    overlap their execution on the GPU, significantly reducing the total latency.
    This is especially effective for the specified "launch-bound tiny operator"
    problem, where the GPU would otherwise be underutilized by sequential kernel
    launches.

    This approach is superior to the baselines because it:
    1.  Avoids explicit memory copies (e.g., .contiguous()) which are expensive for
        the non-contiguous inputs that arise from fused QKV projections.
    2.  Avoids the high memory traffic overhead of a torch.cat operation, which
        would be an alternative but less efficient fusion strategy.
    3.  Directly addresses the launch-bound nature of the problem by parallelizing
        the two independent `flashinfer.norm.rmsnorm` calls.

    Args:
        q: Query tensor of arbitrary shape. May be non-contiguous.
        k: Key tensor of arbitrary shape. May be non-contiguous.
        norm_weight: Normalization weight tensor of shape (hidden_dim,)

    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    # `torch.empty_like` preserves the memory layout (strides) of the input
    # tensors. This is crucial because `flashinfer.norm.rmsnorm`'s `out`
    # parameter expects a tensor with a compatible layout to write the results
    # to, especially for non-contiguous inputs.
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    # Retrieve the persistent CUDA streams to minimize creation overhead.
    s_q, s_k = _get_qknorm_streams()

    # Enqueue the RMSNorm operation for the query tensor on the first stream.
    with torch.cuda.stream(s_q):
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)

    # Enqueue the RMSNorm operation for the key tensor on the second stream.
    with torch.cuda.stream(s_k):
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)

    # The default stream (where the calling code executes) must wait for the
    # operations on `s_q` and `s_k` to complete before any subsequent
    # operation can safely use the results `q_o` and `k_o`.
    # `wait_stream` enqueues a wait dependency in the default stream's command
    # queue and is non-blocking for the host CPU, ensuring efficient execution.
    current_stream = torch.cuda.current_stream()
    current_stream.wait_stream(s_q)
    current_stream.wait_stream(s_k)

    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict indicating the path to the file containing the kernel.
        The evaluator will load this file as a module and call the `qknorm` function.
        """
        return {"program_path": os.path.abspath(__file__)}