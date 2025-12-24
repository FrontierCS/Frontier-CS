import torch
import flashinfer
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dictionary containing the Python code string for an optimized
        qknorm function.
        """
        qknorm_code = textwrap.dedent("""
            import torch
            import flashinfer

            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                \"\"\"
                Apply RMSNorm to query and key tensors using a fused approach.

                This implementation addresses the launch-bound nature of the problem by
                consolidating two separate normalization operations into a single kernel
                launch. It achieves this by concatenating the query (q) and key (k)
                tensors along their non-feature dimension, performing a single RMSNorm
                operation on the fused tensor, and then splitting the result.

                The trade-off is one efficient memory copy (`torch.cat`) in exchange for
                eliminating the overhead of a second kernel launch. For small, memory-bound
                operators, this significantly improves performance.

                Args:
                    q: Query tensor of arbitrary shape.
                    k: Key tensor of arbitrary shape.
                    norm_weight: Normalization weight tensor of shape (hidden_dim,).

                Returns:
                    A tuple of (q_normalized, k_normalized) tensors.
                \"\"\"
                # Preserve original shapes for reshaping the final output
                q_shape = q.shape
                k_shape = k.shape
                hidden_dim = q.shape[-1]
                
                # Reshape q and k to 2D tensors (num_tokens, hidden_dim).
                # .view() is a zero-copy operation that works for the expected
                # memory layouts from fused QKV projections.
                q_2d = q.view(-1, hidden_dim)
                k_2d = k.view(-1, hidden_dim)
                
                num_q_tokens = q_2d.shape[0]

                # Fuse q and k into a single tensor. This operation may copy data but
                # is the key to reducing kernel launch overhead from two to one.
                qk_fused = torch.cat([q_2d, k_2d], dim=0)

                # Allocate a single contiguous output buffer for the fused operation.
                out_fused = torch.empty_like(qk_fused)

                # Perform RMSNorm in a single kernel launch on the fused tensor.
                flashinfer.norm.rmsnorm(qk_fused, norm_weight, out=out_fused)

                # Split the normalized output back into q and k components.
                # Slicing creates zero-copy views into the output buffer.
                q_norm_2d = out_fused[:num_q_tokens]
                k_norm_2d = out_fused[num_q_tokens:]
                
                # Reshape the normalized views back to their original shapes.
                # This is also a zero-copy operation.
                q_normalized = q_norm_2d.view(q_shape)
                k_normalized = k_norm_2d.view(k_shape)

                return q_normalized, k_normalized
        """)
        return {"code": qknorm_code}
