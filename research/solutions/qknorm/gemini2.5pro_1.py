import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = """
import torch
import flashinfer

# By creating streams at the module level, we avoid the overhead of creating
# new streams on every function call, which is crucial for a "launch-bound"
# operator that might be called in a tight loop.
_qknorm_stream_q = torch.cuda.Stream()
_qknorm_stream_k = torch.cuda.Stream()

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    \"\"\"
    Apply RMSNorm to query and key tensors.
    
    This implementation optimizes the QKNorm operation by executing the RMSNorm
    for the query (q) and key (k) tensors concurrently on separate CUDA streams.
    This parallelism is key to overcoming the launch-bound nature of this small
    operator, especially on modern GPUs that can execute multiple kernels
    simultaneously.

    Key Optimizations:
    1.  **Concurrent Execution**: Two CUDA streams are used to launch the
        `flashinfer.norm.rmsnorm` kernels for `q` and `k` without waiting for
        the other to complete. This can lead to a significant speedup,
        approaching 2x if the workload is balanced and the GPU has available
        resources.
    2.  **No Memory Copies**: This approach avoids creating copies of the input
        tensors (e.g., via `torch.cat` or `.contiguous()`), which would double
        the memory traffic. It directly works on the (potentially
        non-contiguous) input tensors, leveraging flashinfer's ability to handle
        such cases efficiently.
    3.  **Reduced Overhead**: Streams are created once at the module level to
        amortize their creation cost over multiple calls to `qknorm`.
    4.  **Correct Synchronization**: The function ensures that the calling stream
        waits for the completion of both normalization kernels before returning,
        guaranteeing that the output tensors are fully computed and ready for
        subsequent operations.

    Args:
        q: Query tensor of arbitrary shape (will be reshaped to 2D internally
           by flashinfer).
        k: Key tensor of arbitrary shape (will be reshaped to 2D internally
           by flashinfer).
        norm_weight: Normalization weight tensor of shape (hidden_dim,).
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors with the same shapes
        as the input q and k.
    \"\"\"
    # Allocate output tensors. `empty_like` preserves the memory layout (strides)
    # and shape of the original tensors, which is what we want.
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)
    
    # The default stream is the stream from which this function was called.
    # We will need to synchronize with it before returning.
    current_stream = torch.cuda.current_stream()

    # Launch the RMSNorm for Q on its dedicated stream. The `with` block
    # sets the current stream for the enclosed operations.
    with torch.cuda.stream(_qknorm_stream_q):
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        
    # Launch the RMSNorm for K on its dedicated stream, allowing it to run
    # concurrently with the normalization of Q.
    with torch.cuda.stream(_qknorm_stream_k):
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        
    # To ensure that the results are available to the caller on the default
    # stream, we must make the default stream wait for our worker streams.
    # This synchronization is essential for correctness and for accurate timing
    # during evaluation.
    current_stream.wait_stream(_qknorm_stream_q)
    current_stream.wait_stream(_qknorm_stream_k)
    
    return q_o, k_o
"""
        return {"code": code}