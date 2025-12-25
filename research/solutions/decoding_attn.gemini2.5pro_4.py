import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # A range of configurations to cover different sequence lengths and hardware characteristics
        triton.Config({'BLOCK_N': 64, 'num_warps': 4, 'num_stages': S}) for S in [1, 2, 4]
    ] + [
        triton.Config({'BLOCK_N': 128, 'num_warps': 4, 'num_stages': S}) for S in [1, 2, 4]
    ] + [
        triton.Config({'BLOCK_N': 256, 'num_warps': 4, 'num_stages': S}) for S in [1, 2, 4]
    ] + [
        triton.Config({'BLOCK_N': 64, 'num_warps': 8, 'num_stages': S}) for S in [1, 2, 4]
    ] + [
        triton.Config({'BLOCK_N': 128, 'num_warps': 8, 'num_stages': S}) for S in [1, 2, 3]
    ] + [
        triton.Config({'BLOCK_N': 256, 'num_warps': 8, 'num_stages': S}) for S in [1, 2]
    ],
    key=['N'],
)
@triton.jit
def _fwd_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N,
    D_HEAD: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # This program computes attention for one head in the batch.
    # The grid is 1D, with size Z * H.
    pid_zh = tl.program_id(0)
    
    # Decompose program ID to get batch and head indices.
    z = pid_zh // H
    h = pid_zh % H

    # Pointers to the current head's data for Q, K, V, O.
    # Since M=1, the m-dimension offset is always 0.
    q_ptr = Q + z * stride_qz + h * stride_qh
    o_ptr = O + z * stride_oz + h * stride_oh
    k_ptr_base = K + z * stride_kz + h * stride_kh
    v_ptr_base = V + z * stride_vz + h * stride_vh

    # Accumulators for the online softmax algorithm.
    # All intermediate computations are done in float32 for precision.
    acc = tl.zeros([D_HEAD], dtype=tl.float32)
    m_i = -float('inf')
    l_i = 0.0

    # Load the query vector for the current head. It's used throughout the loop.
    offs_d = tl.arange(0, D_HEAD)
    q = tl.load(q_ptr + offs_d * stride_qd, mask=offs_d < D_HEAD)
    q_f32 = q.to(tl.float32)
    
    # Loop over the key/value sequence in blocks of size BLOCK_N.
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        current_offs_n = start_n + offs_n
        # Mask for handling sequences that are not a multiple of BLOCK_N.
        n_mask = current_offs_n < N

        # --- Step 1: Load a block of keys (K) ---
        k_ptrs = k_ptr_base + (current_offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)

        # --- Step 2: Compute scores (S = Q @ K.T) ---
        k_f32 = k.to(tl.float32)
        s = tl.sum(q_f32[None, :] * k_f32, 1)
        s *= (D_HEAD**-0.5)
        # Mask out scores for padding tokens before softmax calculations.
        s = tl.where(n_mask, s, -float('inf'))

        # --- Step 3: Online softmax update ---
        # Find the new maximum score.
        m_i_new = tl.maximum(m_i, tl.max(s, 0))
        # Calculate probabilities for the current block.
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(s - m_i_new)
        
        # Rescale the previous accumulator and normalizer.
        acc *= alpha
        # Update the normalizer.
        l_i = l_i * alpha + tl.sum(p, 0)
        
        # --- Step 4: Load a block of values (V) ---
        v_ptrs = v_ptr_base + (current_offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        
        # --- Step 5: Update the output accumulator (acc += P @ V) ---
        v_f32 = v.to(tl.float32)
        acc += tl.dot(p, v_f32)
        
        # Update the max for the next iteration.
        m_i = m_i_new

    # --- Final Step: Normalization and Store ---
    # Finalize the output by dividing by the sum of probabilities.
    l_i = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i

    # Store the final output vector.
    o_ptrs = o_ptr + offs_d * stride_od
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=offs_d < D_HEAD)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    \"\"\"
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    assert M == 1, "This kernel is optimized for M=1 (decoding)."
    assert Dq == Dv, "Dq and Dv must be equal for this implementation."
    D_HEAD = Dq

    # Create the output tensor.
    O = torch.empty_like(Q)

    # The grid defines how many instances of the kernel to launch.
    # We launch one instance per head per batch item.
    grid = lambda META: (Z * H,)
    
    # Launch the Triton kernel.
    _fwd_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        D_HEAD=D_HEAD,
    )
    return O
"""
        return {"code": kernel_code}
