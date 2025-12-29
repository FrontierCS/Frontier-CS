import torch
import triton
import triton.language as tl
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        code = textwrap.dedent("""
        import torch
        import triton
        import triton.language as tl

        @triton.autotune(
            configs=[
                triton.Config({'BN': 32}, num_warps=2),
                triton.Config({'BN': 64}, num_warps=4),
                triton.Config({'BN': 128}, num_warps=4),
                triton.Config({'BN': 256}, num_warps=8),
            ],
            key=['N', 'D', 'DV'],
        )
        @triton.jit
        def _ragged_fwd_kernel(
            Q, K, V, O,
            ROW_LENS,
            stride_qm, stride_qd,
            stride_kn, stride_kd,
            stride_vn, stride_vdv,
            stride_om, stride_odv,
            M, N, D, DV,
            BN: tl.constexpr,
        ):
            # Each program instance computes one row of the output matrix.
            # The row index is determined by the program ID.
            pid_m = tl.program_id(0)

            # Load the specific row length for this query. This is the core of ragged attention.
            row_len = tl.load(ROW_LENS + pid_m)

            # If row_len is 0, the output for this row is a zero vector.
            # We can handle this by writing zeros and exiting early.
            if row_len == 0:
                o_offs = pid_m * stride_om + tl.arange(0, DV)
                o_ptrs = O + o_offs[None, :]
                tl.store(o_ptrs, tl.zeros([1, DV], dtype=O.dtype.element_ty), mask=tl.arange(0, DV)[None, :] < DV)
                return

            # Load the query vector for the current row.
            # This vector is kept in SRAM throughout the computation for this row.
            q_offs = pid_m * stride_qm + tl.arange(0, D)
            q = tl.load(Q + q_offs)

            # Initialize accumulators for the streaming softmax algorithm.
            # All accumulations are done in float32 for numerical stability.
            q = q.to(tl.float32)
            m_i = -float('inf')
            l_i = tl.zeros([1], dtype=tl.float32)
            acc = tl.zeros([1, DV], dtype=tl.float32)

            # The attention scaling factor.
            scale = (D ** -0.5)

            # Offsets for the key/value blocks.
            offs_k = tl.arange(0, BN)

            # Loop over the key/value sequence in blocks of size BN.
            for start_n in range(0, N, BN):
                # -- Load K and V blocks from global memory --
                k_ptrs = K + (start_n + offs_k)[:, None] * stride_kn + tl.arange(0, D)[None, :]
                v_ptrs = V + (start_n + offs_k)[:, None] * stride_vn + tl.arange(0, DV)[None, :]
                
                # Boundary checks for K and V blocks.
                mask_kv = (start_n + offs_k)[:, None] < N
                k = tl.load(k_ptrs, mask=mask_kv, other=0.0)
                v = tl.load(v_ptrs, mask=mask_kv, other=0.0)

                # -- Compute attention scores (Q @ K.T) --
                scores = tl.dot(q.reshape(1, D), tl.trans(k.to(tl.float32)))
                scores *= scale

                # -- Apply the ragged attention mask --
                # Scores for keys beyond the row's specific length are set to -inf.
                ragged_mask = (start_n + offs_k) < row_len
                scores = tl.where(ragged_mask[None, :], scores, -float('inf'))

                # -- Streaming softmax update --
                # This approach avoids materializing the full score matrix, saving memory
                # and improving numerical stability.
                # 1. Find the new maximum score in the current block.
                m_i_new = tl.maximum(m_i, tl.max(scores, 1))
                # 2. Compute probabilities with the new maximum for stability.
                p = tl.exp(scores - m_i_new[:, None])
                # 3. Rescale the old softmax denominator.
                alpha = tl.exp(m_i - m_i_new)
                # 4. Compute the new softmax denominator.
                l_i_new = alpha * l_i + tl.sum(p, 1)

                # -- Update the accumulator --
                # 1. Rescale the old accumulator value.
                acc = acc * alpha[:, None]
                # 2. Add the weighted values from the current block.
                p_cast = p.to(v.dtype)
                acc += tl.dot(p_cast, v)

                # 3. Update the max and denominator for the next iteration.
                m_i = m_i_new
                l_i = l_i_new

            # Finalize the accumulator by dividing by the softmax denominator.
            # Handle the case where l_i might be zero to avoid division by zero.
            l_i = tl.where(l_i == 0, 1.0, l_i)
            acc = acc / l_i[:, None]

            # -- Write the final output block to global memory --
            o_offs = pid_m * stride_om + tl.arange(0, DV)
            o_ptrs = O + o_offs[None, :]
            tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=tl.arange(0, DV)[None, :] < DV)


        def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
            \"\"\"
            Ragged attention computation.
            
            Args:
                Q: Query tensor of shape (M, D) - query features (float16)
                K: Key tensor of shape (N, D) - key features (float16)
                V: Value tensor of shape (N, Dv) - value features (float16)
                row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
            
            Returns:
                Output tensor of shape (M, Dv) - attention output (float16)
            \"\"\"
            M, D = Q.shape
            N, _ = K.shape
            _, DV = V.shape

            # Allocate the output tensor.
            O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

            # The grid for the kernel is one program per query row.
            grid = (M,)

            # Launch the Triton kernel.
            # Triton's autotuner will automatically select the best block size (BN)
            # based on the provided configurations and input shapes.
            _ragged_fwd_kernel[grid](
                Q, K, V, O,
                row_lens,
                Q.stride(0), Q.stride(1),
                K.stride(0), K.stride(1),
                V.stride(0), V.stride(1),
                O.stride(0), O.stride(1),
                M, N, D, DV,
            )

            return O
        """)
        return {"code": code}