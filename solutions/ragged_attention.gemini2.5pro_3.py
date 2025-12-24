import torch
import triton
import triton.language as tl
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _ragged_kernel(
                Q, K, V, O, ROW_LENS,
                stride_qm, stride_qd,
                stride_kn, stride_kd,
                stride_vn, stride_vd,
                stride_om, stride_od,
                stride_rl,
                M, N, D, DV,
                # Meta-parameters
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_D: tl.constexpr,
                BLOCK_DV: tl.constexpr,
            ):
                # This program computes a BLOCK_M x DV block of the output matrix O.
                # Each program instance handles a unique block of M (query rows).
                pid_m = tl.program_id(0)

                # Offsets for the current program
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_d = tl.arange(0, BLOCK_D)
                offs_dv = tl.arange(0, BLOCK_DV)

                # Pointers to Q, O, and row_lens
                q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                row_lens_ptrs = ROW_LENS + offs_m * stride_rl

                # Mask for rows in Q, O that are within the M dimension.
                # This handles the case where M is not a multiple of BLOCK_M.
                m_mask = offs_m < M

                # Load the specific row lengths for this block of queries.
                row_len = tl.load(row_lens_ptrs, mask=m_mask, other=0)

                # Initialize accumulator and softmax statistics in float32 for precision.
                acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)

                # Attention scale factor.
                scale = (D) ** -0.5
                
                # Load Q block for this program. This block is reused across the inner loop.
                q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)

                # Loop over K and V in blocks of size BLOCK_N.
                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    n_boundary_mask = offs_n < N
                    
                    # Load K block (transposed for efficient dot product).
                    k_ptrs = K + offs_d[:, None] * stride_kd + offs_n[None, :] * stride_kn
                    k = tl.load(k_ptrs, mask=n_boundary_mask[None, :], other=0.0)
                    
                    # Load V block.
                    v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=n_boundary_mask[:, None], other=0.0)
                    
                    # Compute attention scores: S = (Q @ K^T) * scale.
                    s_ij = tl.dot(q, k, out_dtype=tl.float32) * scale
                    
                    # Apply the ragged attention mask. This is the core logic for variable length.
                    # Scores for columns j >= row_len[i] are set to -inf.
                    ragged_mask = offs_n[None, :] < row_len[:, None]
                    s_ij = tl.where(ragged_mask, s_ij, -float("inf"))

                    # --- Streaming softmax update ---
                    # 1. Find new max score for the row.
                    m_ij = tl.max(s_ij, 1)
                    m_new = tl.maximum(m_i, m_ij)
                    
                    # 2. Rescale previous statistics and compute new probabilities.
                    alpha = tl.exp(m_i - m_new)
                    p_ij = tl.exp(s_ij - m_new[:, None])
                    
                    # 3. Update the softmax normalizer.
                    l_i_new = alpha * l_i + tl.sum(p_ij, 1)
                    
                    # 4. Update the accumulator.
                    # Rescale old accumulator to match the new max value.
                    acc = acc * alpha[:, None]
                    # Add new values, weighted by their probabilities.
                    p_ij_casted = p_ij.to(Q.dtype.element_ty)
                    acc += tl.dot(p_ij_casted, v)
                    
                    # 5. Update state for the next iteration.
                    l_i = l_i_new
                    m_i = m_new

                # Finalize the output.
                # Normalize the accumulator by the final sum of probabilities.
                # Handle the case where a row has zero length and l_i is 0 to avoid division by zero.
                l_i_safe = tl.where(l_i == 0, 1.0, l_i)
                acc = acc / l_i_safe[:, None]
                
                # Write the final output block to global memory.
                tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=m_mask[:, None])

            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                M, D = Q.shape
                N, _ = K.shape
                _, DV = V.shape
                
                O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

                # Configuration for the Triton kernel.
                # These values are chosen based on the problem constraints and target GPU (NVIDIA L4).
                # A larger BLOCK_M increases parallelism within a block.
                # A moderate BLOCK_N balances cache usage and loop overhead.
                BLOCK_M = 128
                BLOCK_N = 64
                num_warps = 4
                num_stages = 2
                
                grid = (triton.cdiv(M, BLOCK_M),)

                # Launch the kernel.
                _ragged_kernel[grid](
                    Q, K, V, O, row_lens,
                    Q.stride(0), Q.stride(1),
                    K.stride(0), K.stride(1),
                    V.stride(0), V.stride(1),
                    O.stride(0), O.stride(1),
                    row_lens.stride(0),
                    M, N, D, DV,
                    # Pass constants as meta-parameters.
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_D=D,
                    BLOCK_DV=DV,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )
                return O
        """)
        return {"code": kernel_code}
